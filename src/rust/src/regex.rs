//! A small, dependency-free regular-expression engine.
//!
//! The Ago standard library is intentionally free of external crates (so the
//! package builds hermetically), so rather than pull in the `regex` crate we
//! implement a compact backtracking bytecode VM in the style of Russ Cox's
//! "Regular Expression Matching: the Virtual Machine Approach".
//!
//! Supported syntax:
//!   - literals and `.` (any char except newline)
//!   - escapes: `\d \D \w \W \s \S` plus `\` before any metachar to take it
//!     literally (`\.`, `\(`, `\\`, `\n`, `\t`, `\r`, ...)
//!   - character classes `[abc]`, ranges `[a-z]`, negation `[^...]`, and the
//!     `\d \w \s` shorthands inside classes
//!   - anchors `^` (start of text) and `$` (end of text)
//!   - groups `(...)` (capturing) and `(?:...)` (non-capturing), alternation `|`
//!   - greedy quantifiers `*` `+` `?` and counted `{n}` `{n,}` `{n,m}`
//!
//! Two Ago-facing entry points live in `functions`-style wrappers below:
//!   - `congruam(text, pattern)` -> Bool: does the pattern match anywhere?
//!   - `congruum(text, pattern)` -> list of matches, each a string list whose
//!     element 0 is the whole match and elements 1.. are the capture groups.

use crate::types::AgoType;

// ---------------------------------------------------------------------------
// AST
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
enum ClassItem {
    Ch(char),
    Range(char, char),
    Digit,
    NotDigit,
    Word,
    NotWord,
    Space,
    NotSpace,
}

#[derive(Debug, Clone)]
enum Atom {
    Char(char),
    Any,
    Class { negated: bool, items: Vec<ClassItem> },
    Group { capture: Option<usize>, alts: Vec<Vec<Piece>> },
    Start,
    End,
}

#[derive(Debug, Clone)]
struct Piece {
    atom: Atom,
    min: usize,
    max: Option<usize>, // None == unbounded
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

struct Parser {
    chars: Vec<char>,
    pos: usize,
    group_count: usize, // number of capturing groups seen so far
}

impl Parser {
    fn new(pattern: &str) -> Self {
        Parser {
            chars: pattern.chars().collect(),
            pos: 0,
            group_count: 0,
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn next(&mut self) -> Option<char> {
        let c = self.chars.get(self.pos).copied();
        if c.is_some() {
            self.pos += 1;
        }
        c
    }

    /// Parse a full alternation (top level or inside a group).
    fn parse_alts(&mut self) -> Result<Vec<Vec<Piece>>, String> {
        let mut alts = vec![self.parse_seq()?];
        while self.peek() == Some('|') {
            self.next();
            alts.push(self.parse_seq()?);
        }
        Ok(alts)
    }

    fn parse_seq(&mut self) -> Result<Vec<Piece>, String> {
        let mut pieces = Vec::new();
        while let Some(c) = self.peek() {
            if c == '|' || c == ')' {
                break;
            }
            pieces.push(self.parse_piece()?);
        }
        Ok(pieces)
    }

    fn parse_piece(&mut self) -> Result<Piece, String> {
        let atom = self.parse_atom()?;
        let (min, max) = self.parse_quantifier()?;
        Ok(Piece { atom, min, max })
    }

    fn parse_quantifier(&mut self) -> Result<(usize, Option<usize>), String> {
        match self.peek() {
            Some('*') => {
                self.next();
                Ok((0, None))
            }
            Some('+') => {
                self.next();
                Ok((1, None))
            }
            Some('?') => {
                self.next();
                Ok((0, Some(1)))
            }
            Some('{') => self.parse_counted(),
            _ => Ok((1, Some(1))),
        }
    }

    fn parse_counted(&mut self) -> Result<(usize, Option<usize>), String> {
        // Already at '{'. Parse {n}, {n,}, {n,m}.
        let save = self.pos;
        self.next(); // consume '{'
        let mut min_s = String::new();
        while let Some(c) = self.peek() {
            if c.is_ascii_digit() {
                min_s.push(c);
                self.next();
            } else {
                break;
            }
        }
        if min_s.is_empty() {
            // Not a valid quantifier; treat '{' as a literal by rewinding.
            self.pos = save;
            return Ok((1, Some(1)));
        }
        let min: usize = min_s.parse().map_err(|_| "bad {n}".to_string())?;
        let max;
        if self.peek() == Some(',') {
            self.next();
            let mut max_s = String::new();
            while let Some(c) = self.peek() {
                if c.is_ascii_digit() {
                    max_s.push(c);
                    self.next();
                } else {
                    break;
                }
            }
            max = if max_s.is_empty() {
                None
            } else {
                Some(max_s.parse().map_err(|_| "bad {n,m}".to_string())?)
            };
        } else {
            max = Some(min);
        }
        if self.peek() != Some('}') {
            // Malformed; rewind and treat '{' literally.
            self.pos = save;
            return Ok((1, Some(1)));
        }
        self.next(); // consume '}'
        Ok((min, max))
    }

    fn parse_atom(&mut self) -> Result<Atom, String> {
        let c = self.next().ok_or("unexpected end of pattern")?;
        match c {
            '(' => {
                // Non-capturing group?
                let capture = if self.peek() == Some('?') && self.chars.get(self.pos + 1) == Some(&':')
                {
                    self.next(); // ?
                    self.next(); // :
                    None
                } else {
                    self.group_count += 1;
                    Some(self.group_count)
                };
                let alts = self.parse_alts()?;
                if self.next() != Some(')') {
                    return Err("missing closing ')'".to_string());
                }
                Ok(Atom::Group { capture, alts })
            }
            '[' => self.parse_class(),
            '.' => Ok(Atom::Any),
            '^' => Ok(Atom::Start),
            '$' => Ok(Atom::End),
            '\\' => {
                let e = self.next().ok_or("dangling backslash")?;
                Ok(escape_atom(e))
            }
            _ => Ok(Atom::Char(c)),
        }
    }

    fn parse_class(&mut self) -> Result<Atom, String> {
        // '[' already consumed.
        let negated = if self.peek() == Some('^') {
            self.next();
            true
        } else {
            false
        };
        let mut items = Vec::new();
        loop {
            let c = match self.next() {
                Some(']') => break,
                Some(c) => c,
                None => return Err("unterminated character class".to_string()),
            };
            if c == '\\' {
                let e = self.next().ok_or("dangling backslash in class")?;
                match e {
                    'd' => items.push(ClassItem::Digit),
                    'D' => items.push(ClassItem::NotDigit),
                    'w' => items.push(ClassItem::Word),
                    'W' => items.push(ClassItem::NotWord),
                    's' => items.push(ClassItem::Space),
                    'S' => items.push(ClassItem::NotSpace),
                    'n' => items.push(ClassItem::Ch('\n')),
                    't' => items.push(ClassItem::Ch('\t')),
                    'r' => items.push(ClassItem::Ch('\r')),
                    other => items.push(ClassItem::Ch(other)),
                }
                continue;
            }
            // Range a-z (but not if '-' is the last char before ']').
            if self.peek() == Some('-') && self.chars.get(self.pos + 1) != Some(&']') {
                self.next(); // consume '-'
                let end = self.next().ok_or("bad range")?;
                items.push(ClassItem::Range(c, end));
            } else {
                items.push(ClassItem::Ch(c));
            }
        }
        Ok(Atom::Class { negated, items })
    }
}

fn escape_atom(e: char) -> Atom {
    match e {
        'd' => Atom::Class {
            negated: false,
            items: vec![ClassItem::Digit],
        },
        'D' => Atom::Class {
            negated: false,
            items: vec![ClassItem::NotDigit],
        },
        'w' => Atom::Class {
            negated: false,
            items: vec![ClassItem::Word],
        },
        'W' => Atom::Class {
            negated: false,
            items: vec![ClassItem::NotWord],
        },
        's' => Atom::Class {
            negated: false,
            items: vec![ClassItem::Space],
        },
        'S' => Atom::Class {
            negated: false,
            items: vec![ClassItem::NotSpace],
        },
        'n' => Atom::Char('\n'),
        't' => Atom::Char('\t'),
        'r' => Atom::Char('\r'),
        other => Atom::Char(other),
    }
}

fn class_item_matches(item: &ClassItem, c: char) -> bool {
    match item {
        ClassItem::Ch(x) => *x == c,
        ClassItem::Range(a, b) => *a <= c && c <= *b,
        ClassItem::Digit => c.is_ascii_digit(),
        ClassItem::NotDigit => !c.is_ascii_digit(),
        ClassItem::Word => c.is_alphanumeric() || c == '_',
        ClassItem::NotWord => !(c.is_alphanumeric() || c == '_'),
        ClassItem::Space => c.is_whitespace(),
        ClassItem::NotSpace => !c.is_whitespace(),
    }
}

// ---------------------------------------------------------------------------
// Compiler: AST -> bytecode
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
enum Inst {
    Char(char),
    Any,
    Class { negated: bool, items: Vec<ClassItem> },
    Start,
    End,
    Save(usize),
    Jmp(usize),
    Split(usize, usize), // prefer first
    Match,
}

struct Program {
    insts: Vec<Inst>,
    ngroups: usize, // includes group 0 (whole match)
}

fn compile_seq(seq: &[Piece], insts: &mut Vec<Inst>) {
    for piece in seq {
        compile_piece(piece, insts);
    }
}

fn compile_atom(atom: &Atom, insts: &mut Vec<Inst>) {
    match atom {
        Atom::Char(c) => insts.push(Inst::Char(*c)),
        Atom::Any => insts.push(Inst::Any),
        Atom::Class { negated, items } => insts.push(Inst::Class {
            negated: *negated,
            items: items.clone(),
        }),
        Atom::Start => insts.push(Inst::Start),
        Atom::End => insts.push(Inst::End),
        Atom::Group { capture, alts } => {
            if let Some(idx) = capture {
                insts.push(Inst::Save(2 * idx));
            }
            compile_alts_inline(alts, insts);
            if let Some(idx) = capture {
                insts.push(Inst::Save(2 * idx + 1));
            }
        }
    }
}

/// Compile an alternation inline (used for groups), patching branch jumps to the
/// instruction following the whole alternation.
fn compile_alts_inline(alts: &[Vec<Piece>], insts: &mut Vec<Inst>) {
    let mut jmp_fixups = Vec::new();
    for i in 0..alts.len() {
        let last = i == alts.len() - 1;
        if last {
            compile_seq(&alts[i], insts);
        } else {
            let split_pc = insts.len();
            insts.push(Inst::Split(0, 0));
            let branch_start = insts.len();
            compile_seq(&alts[i], insts);
            let jmp_pc = insts.len();
            insts.push(Inst::Jmp(0));
            jmp_fixups.push(jmp_pc);
            let next_start = insts.len();
            if let Inst::Split(a, b) = &mut insts[split_pc] {
                *a = branch_start;
                *b = next_start;
            }
        }
    }
    let end = insts.len();
    for pc in jmp_fixups {
        if let Inst::Jmp(t) = &mut insts[pc] {
            *t = end;
        }
    }
}

fn compile_piece(piece: &Piece, insts: &mut Vec<Inst>) {
    let min = piece.min;
    let max = piece.max;

    // Emit `min` mandatory copies.
    for _ in 0..min {
        compile_atom(&piece.atom, insts);
    }

    match max {
        None => {
            // Unbounded tail: greedy star.
            // L: Split(body, after); body; Jmp(L); after:
            let l = insts.len();
            insts.push(Inst::Split(0, 0));
            let body = insts.len();
            compile_atom(&piece.atom, insts);
            insts.push(Inst::Jmp(l));
            let after = insts.len();
            if let Inst::Split(a, b) = &mut insts[l] {
                *a = body;
                *b = after;
            }
        }
        Some(m) => {
            // (m - min) optional copies, each guarded by a Split to `end`.
            let optional = m.saturating_sub(min);
            let mut split_pcs = Vec::new();
            for _ in 0..optional {
                let s = insts.len();
                insts.push(Inst::Split(0, 0));
                split_pcs.push(s);
                let body = insts.len();
                compile_atom(&piece.atom, insts);
                if let Inst::Split(a, _) = &mut insts[s] {
                    *a = body;
                }
            }
            let end = insts.len();
            for s in split_pcs {
                if let Inst::Split(_, b) = &mut insts[s] {
                    *b = end;
                }
            }
        }
    }
}

fn compile_program(pattern: &str) -> Result<Program, String> {
    let mut parser = Parser::new(pattern);
    let alts = parser.parse_alts()?;
    if parser.pos != parser.chars.len() {
        return Err("unexpected trailing characters in pattern".to_string());
    }
    let ngroups = parser.group_count + 1; // +1 for whole-match group 0
    let mut insts = Vec::new();
    insts.push(Inst::Save(0));
    compile_alts_inline(&alts, &mut insts);
    insts.push(Inst::Save(1));
    insts.push(Inst::Match);
    Ok(Program { insts, ngroups })
}

// ---------------------------------------------------------------------------
// Backtracking VM
// ---------------------------------------------------------------------------

fn run(
    prog: &[Inst],
    mut pc: usize,
    text: &[char],
    mut sp: usize,
    saves: &mut Vec<Option<usize>>,
) -> bool {
    loop {
        match &prog[pc] {
            Inst::Char(c) => {
                if sp < text.len() && text[sp] == *c {
                    pc += 1;
                    sp += 1;
                } else {
                    return false;
                }
            }
            Inst::Any => {
                if sp < text.len() && text[sp] != '\n' {
                    pc += 1;
                    sp += 1;
                } else {
                    return false;
                }
            }
            Inst::Class { negated, items } => {
                if sp < text.len() {
                    let c = text[sp];
                    let mut matched = items.iter().any(|it| class_item_matches(it, c));
                    if *negated {
                        matched = !matched;
                    }
                    if matched {
                        pc += 1;
                        sp += 1;
                    } else {
                        return false;
                    }
                } else {
                    return false;
                }
            }
            Inst::Start => {
                if sp == 0 {
                    pc += 1;
                } else {
                    return false;
                }
            }
            Inst::End => {
                if sp == text.len() {
                    pc += 1;
                } else {
                    return false;
                }
            }
            Inst::Match => return true,
            Inst::Jmp(t) => pc = *t,
            Inst::Split(a, b) => {
                if run(prog, *a, text, sp, saves) {
                    return true;
                }
                pc = *b;
            }
            Inst::Save(slot) => {
                let slot = *slot;
                let old = saves[slot];
                saves[slot] = Some(sp);
                if run(prog, pc + 1, text, sp, saves) {
                    return true;
                }
                saves[slot] = old;
                return false;
            }
        }
    }
}

/// Try to match the program starting exactly at `start`. On success returns the
/// capture slots (length 2*ngroups).
fn try_match_at(prog: &Program, text: &[char], start: usize) -> Option<Vec<Option<usize>>> {
    let mut saves = vec![None; prog.ngroups * 2];
    if run(&prog.insts, 0, text, start, &mut saves) {
        Some(saves)
    } else {
        None
    }
}

// ---------------------------------------------------------------------------
// Ago-facing API
// ---------------------------------------------------------------------------

/// Does `pattern` match anywhere in `text`?  Name ends in -am (returns bool).
pub fn congruam(text: &AgoType, pattern: &AgoType) -> AgoType {
    let (t, p) = match (text, pattern) {
        (AgoType::String(t), AgoType::String(p)) => (t, p),
        _ => panic!("congruam expects two Strings, got {:?} and {:?}", text, pattern),
    };
    let prog = match compile_program(p) {
        Ok(prog) => prog,
        Err(e) => panic!("invalid regex pattern {:?}: {}", p, e),
    };
    let chars: Vec<char> = t.chars().collect();
    for start in 0..=chars.len() {
        if try_match_at(&prog, &chars, start).is_some() {
            return AgoType::Bool(true);
        }
    }
    AgoType::Bool(false)
}

/// All non-overlapping matches of `pattern` in `text`. Name ends in -uum
/// (returns list_any). Each match is a string list: element 0 is the whole
/// match, elements 1.. are the capture groups (empty string if a group did not
/// participate in the match).
pub fn congruum(text: &AgoType, pattern: &AgoType) -> AgoType {
    let (t, p) = match (text, pattern) {
        (AgoType::String(t), AgoType::String(p)) => (t, p),
        _ => panic!("congruum expects two Strings, got {:?} and {:?}", text, pattern),
    };
    let prog = match compile_program(p) {
        Ok(prog) => prog,
        Err(e) => panic!("invalid regex pattern {:?}: {}", p, e),
    };
    let chars: Vec<char> = t.chars().collect();
    let mut matches: Vec<AgoType> = Vec::new();
    let mut start = 0;
    while start <= chars.len() {
        if let Some(saves) = try_match_at(&prog, &chars, start) {
            let whole_start = saves[0].unwrap_or(start);
            let whole_end = saves[1].unwrap_or(start);
            let mut groups: Vec<String> = Vec::with_capacity(prog.ngroups);
            for g in 0..prog.ngroups {
                let s = saves[2 * g];
                let e = saves[2 * g + 1];
                let piece: String = match (s, e) {
                    (Some(s), Some(e)) if e >= s => chars[s..e].iter().collect(),
                    _ => String::new(),
                };
                groups.push(piece);
            }
            matches.push(AgoType::StringList(groups));
            // Advance past this match; for empty matches step one char to avoid
            // looping forever.
            if whole_end > whole_start {
                start = whole_end;
            } else {
                start += 1;
            }
        } else {
            start += 1;
        }
    }
    AgoType::ListAny(matches)
}
