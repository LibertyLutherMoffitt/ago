/**
 * Tree-sitter grammar for Ago, a Latin-inspired language that transpiles to Rust.
 *
 * Mirrors the TatSu grammar used by the compiler (src/AgoParser.py). Ago is
 * newline-sensitive: statements are separated by newlines or semicolons, while
 * spaces, tabs and `#` comments are insignificant.
 */

module.exports = grammar({
  name: 'ago',

  word: $ => $.identifier,

  // Spaces, tabs and comments are insignificant; newlines are NOT (they
  // terminate statements) so they are matched explicitly via `_sep`.
  extras: $ => [/[ \t]/, $.comment],

  conflicts: $ => [
    // At statement start an identifier could begin a reassignment (`x = ...`)
    // or an expression statement (`x`, `x(...)`, `x.foo()`).
    [$.reassignment, $._primary],
  ],

  rules: {
    source_file: $ => seq(
      optional($._sep),
      repeat(seq($._toplevel, $._sep)),
      optional($._toplevel),
    ),

    _sep: _ => repeat1(choice('\n', '\r\n', ';')),

    comment: _ => token(seq('#', /[^\n]*/)),

    _toplevel: $ => choice(
      $.function_definition,
      $._statement,
    ),

    // ---- Statements ----

    _statement: $ => choice(
      $.declaration,
      $.reassignment,
      $.if_statement,
      $.for_statement,
      $.while_statement,
      $.match_statement,
      $.return_statement,
      $.break_statement,
      $.continue_statement,
      $.pass_statement,
      $.expression_statement,
    ),

    declaration: $ => seq(
      field('name', $.identifier),
      repeat(seq(',', field('name', $.identifier))),
      ':=',
      field('value', $._expression),
    ),

    reassignment: $ => seq(
      field('target', $.identifier),
      repeat(seq('[', field('index', $._expression), ']')),
      field('operator', choice('=', '+=', '-=', '*=', '/=', '%=')),
      field('value', $._expression),
    ),

    // `aluid` always follows the closing brace on the same line (`} aluid ...`),
    // so no statement separator is consumed before it.
    if_statement: $ => prec.right(seq(
      'si',
      field('condition', $._expression),
      field('consequence', $.block),
      repeat(seq(
        'aluid',
        field('elif_condition', $._expression),
        field('elif_consequence', $.block),
      )),
      optional(seq(
        'aluid',
        field('alternative', $.block),
      )),
    )),

    for_statement: $ => seq(
      'pro',
      field('iterator', $.identifier),
      optional(seq(',', field('iterator', $.identifier))),
      'in',
      field('iterable', $._expression),
      field('body', $.block),
    ),

    while_statement: $ => seq(
      'dum',
      field('condition', $._expression),
      field('body', $.block),
    ),

    match_statement: $ => seq(
      'discerne',
      field('value', $._expression),
      '{',
      optional($._sep),
      repeat(seq($.match_arm, $._sep)),
      optional($.match_arm),
      '}',
    ),

    match_arm: $ => seq(
      field('pattern', choice('aluid', $._expression)),
      field('body', $.block),
    ),

    return_statement: $ => seq('redeo', field('value', $._expression)),
    break_statement: _ => 'frio',
    continue_statement: _ => 'pergo',
    pass_statement: _ => 'omitto',

    expression_statement: $ => $._expression,

    block: $ => seq(
      '{',
      optional($._sep),
      repeat(seq($._statement, $._sep)),
      optional($._statement),
      '}',
    ),

    // ---- Functions ----

    function_definition: $ => seq(
      'des',
      field('name', $.identifier),
      '(',
      optional($._parameters),
      ')',
      field('body', $.block),
    ),

    lambda: $ => seq(
      'des',
      optional(seq('(', optional($._parameters), ')')),
      field('body', $.block),
    ),

    _parameters: $ => seq(
      $.identifier,
      repeat(seq(',', $.identifier)),
    ),

    // ---- Expressions ----

    _expression: $ => choice(
      $.ternary,
      $.binary_expression,
      $.unary_expression,
      $._postfix,
    ),

    ternary: $ => prec.right(1, seq(
      field('condition', $._expression),
      '?',
      field('consequence', $._expression),
      ':',
      field('alternative', $._expression),
    )),

    binary_expression: $ => {
      const table = [
        ['vel', 2], ['|', 2], ['^', 2], ['?:', 2],
        ['et', 3], ['&', 3],
        ['==', 4], ['!=', 4], ['>=', 4], ['<=', 4], ['<', 4], ['>', 4],
        ['est', 4], ['in', 4],
        ['..', 5], ['.<', 5],
        ['+', 6], ['-', 6],
        ['*', 7], ['/', 7], ['%', 7],
      ];
      return choice(...table.map(([op, p]) => prec.left(p, seq(
        field('left', $._expression),
        field('operator', op),
        field('right', $._expression),
      ))));
    },

    unary_expression: $ => prec.right(8, seq(
      field('operator', choice('-', '+', 'non')),
      field('operand', $._expression),
    )),

    _postfix: $ => choice(
      $.subscript,
      $.member_access,
      $.call,
      $._primary,
    ),

    subscript: $ => prec.left(9, seq(
      field('object', $._postfix),
      '[',
      field('index', $._expression),
      ']',
    )),

    member_access: $ => prec.left(9, seq(
      field('object', $._postfix),
      '.',
      field('member', choice($.method_call, $.identifier, $.string)),
    )),

    method_call: $ => seq(
      field('name', $.identifier),
      '(',
      optional($._arguments),
      ')',
    ),

    call: $ => prec(9, seq(
      field('function', $.identifier),
      '(',
      optional($._arguments),
      ')',
    )),

    _arguments: $ => seq(
      $._expression,
      repeat(seq(',', $._expression)),
    ),

    _primary: $ => choice(
      $.parenthesized_expression,
      $.list,
      $.map,
      $.lambda,
      $.roman_numeral,
      $.it,
      $.identifier,
      $.string,
      $.float,
      $.int,
      $.true,
      $.false,
      $.null,
    ),

    parenthesized_expression: $ => seq('(', $._expression, ')'),

    list: $ => seq(
      '[',
      optional(seq(
        $._expression,
        repeat(seq(',', $._expression)),
        optional(','),
      )),
      ']',
    ),

    map: $ => seq(
      '{',
      optional($._sep),
      repeat(seq($.pair, $._pair_sep)),
      optional($.pair),
      '}',
    ),

    _pair_sep: _ => repeat1(choice(',', '\n', '\r\n', ';')),

    pair: $ => seq(
      field('key', choice($.string, $.identifier)),
      ':',
      field('value', $._expression),
    ),

    // ---- Literals ----

    identifier: _ => /[A-Za-z_][A-Za-z_0-9]*/,

    // Roman numerals are int literals and, as in the reference parser, win over
    // identifiers for all-roman-letter tokens (higher token precedence).
    roman_numeral: _ => token(prec(2, /[MCDLXIV]+/)),

    it: _ => 'id',
    true: _ => 'verum',
    false: _ => 'falsus',
    null: _ => 'inanis',

    float: _ => /[0-9]*\.[0-9]+/,
    int: _ => /[0-9]+/,

    string: _ => token(seq(
      '"',
      repeat(choice(
        /[^"\\\r\n]/,
        seq('\\', /[tnrf"\\]/),
        seq('\\', /[0-7]{3}/),
      )),
      '"',
    )),
  },
});
