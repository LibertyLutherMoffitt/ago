@@grammar :: Ago
@@whitespace :: /[ \t]+/
@@eol_comments :: /(?m)#([^\n]*?)$/
@@left_recursion :: True

@@keyword :: ordo aluid falsus frio id pergo omitto redeo
@@keyword :: si est pro dum cum hoc novus inanis tunc verum
@@keyword :: et vel non des designo in inporto

principio
    =
    [ nl ]
    class_block
    { nl class_block }
    [ nl ]
    $
    ;

class_block
    =
    CLASS name:identifier [ LPAREN base:identifier RPAREN ] LBRACE nl
        vars:{ var_decl }*
        methods:{ method_decl }*
    RBRACE
    ;

var_decl
    =
    name:identifier [ ASSIGNMENT_OP value:expression ] nl
    ;

method_decl
    =
    DEF name:identifier
        LPAREN [ params:expression_list ] RPAREN
        [ returns:type ]
        LBRACE nl
            body:{ statement nl }*
        RBRACE nl
    ;

type
    =
    | base:identifier
    | array:(
        inner:type
        LBRACKET [ size:expression ] RBRACKET
      )
    ;

statement
    =
    | assignment:assignment_stmt
    | if_stmt:if_stmt
    | for_stmt:for_stmt
    | while_stmt:while_stmt
    | call:call_stmt
    | PASS
    | BREAK
    | CONTINUE
    | return_stmt:(RETURN value:expression)
    | var:var_decl
    ;

assignment_stmt
    =
    target:identifier [ index:indexing ]
    op:(ASSIGNMENT_OP | REASSIGNMENT_OP)
    value:expression
    ;

indexing
    =
    indexes:{ LBRACKET expr:expression RBRACKET }+
    ;

if_stmt
    =
    IF cond:expression then:block_body
        elifs:{ ELSE elif_cond:expression elif_body:block_body }*
        [ ELSE else_body:block_body ]
    ;

block_body
    =
    LBRACE nl
        stmts:{ statement nl }*
    RBRACE
    ;

while_stmt
    =
    WHILE cond:expression body:block_body
    ;

for_stmt
    =
    FOR iterator:expression IN iterable:expression body:block_body
    ;

# --- CALLS ---

call_stmt
    =
    [ recv:(receiver:item) PERIOD ]
    first:nodotcall_stmt
    chain:{ PERIOD more:nodotcall_stmt }*
    ;

nodotcall_stmt
    =
    func:identifier LPAREN [ args:expression_list ] RPAREN
    ;

expression_list
    =
    first:expression
    rest:{ COMMA expr:expression }*
    ;

# --- EXPRESSIONS ---

expression = pa ;

pa
    =
    | left:pa op:(OR | BOR | BXOR | ELVIS) right:pb
    | pb
    ;

pb
    =
    | left:pb op:(AND | BAND) right:pc
    | pc
    ;

pc
    =
    | left:pd op:(EQ | GT | GE | LT | LE) right:pd
    | pd
    ;

pd
    =
    | left:pd op:(SLICE | SLICETO) right:pe
    | pe
    ;

pe
    =
    | left:pe op:(PLUS | MINUS) right:pf
    | pf
    ;

pf
    =
    | left:pf op:(TIMES | DIV | MOD) right:pg
    | pg
    ;

pg
    =
    | op:(MINUS | PLUS | NOT) right:pg
    | ph
    ;

ph
    =
    | call:call_stmt
    | new:(NEW new_type:type)
    | value:item
    ;

item
    =
    | paren:(LPAREN expr:expression RPAREN)
    | call:nodotcall_stmt
    | mchain:(
        base:base_ref
        chain:{ PERIOD method:nodotcall_stmt }+
      )
    | indexed:(identifier idx:indexing)
    | id:identifier
    | str:STR_LIT
    | float:FLOATLIT
    | int:INTLIT
    | roman:ROMAN_NUMERAL
    | TRUE
    | FALSE
    | NULL
    | THIS
    | IT
    ;

base_ref
    =
    | THIS
    | IT
    | indexed:(identifier idx:indexing)
    | id:identifier
    ;

nl = { CR }+ ;

@name
identifier = /[A-Za-z_][A-Za-z_0-9]*/ ;


# ---------- lexical rules (tokens) ----------

ROMAN_NUMERAL = /[MCDLXIV]+/ ;
FLOATLIT = /[0-9]*\.[0-9]+/ ;
INTLIT = /[0-9]+/ ;

LPAREN   = '(' ;
RPAREN   = ')' ;
LBRACKET = '[' ;
RBRACKET = ']' ;
LBRACE   = '{' ;
RBRACE   = '}' ;

BAND = '&' ;
BOR  = '|' ;
BXOR = '^' ;
MOD  = '%' ;
PLUS = '+' ;
MINUS = '-' ;
TIMES = '*' ;
DIV   = '/' ;

ELVIS = '?:' ;

SLICE   = '..' ;
SLICETO = '.<' ;
GE = '>=' ;
GT = '>' ;
LE = '<=' ;
LT = '<' ;
EQ = '==' ;

ASSIGNMENT_OP   = ':=' ;
REASSIGNMENT_OP = '=' ;

CLASS   = 'ordo' ;
ELSE    = 'aluid' ;
FALSE   = 'falsus' ;
BREAK   = 'frio' ;
IT      = 'id' ;
CONTINUE = 'pergo' ;
PASS    = 'omitto' ;
RETURN  = 'redeo' ;
IF      = 'si' ;
IS      = 'est' ;
FOR     = 'pro' ;
WHILE   = 'dum' ;
WITH    = 'cum' ;
THIS    = 'hoc' ;
NEW     = 'novus' ;
NULL    = 'inanis' ;
THEN    = 'tunc' ;
TRUE    = 'verum' ;
AND     = 'et' ;
OR      = 'vel' ;
NOT     = 'non' ;
DEF     = 'des' | 'designo' ;
IN      = 'in' ;
IMPORT  = 'inporto' ;

COMMA     = ',' ;
COLON     = ':' ;
SEMICOLON = ';' ;
PERIOD    = '.' ;

CR = /\r?\n/ ;

STR_LIT = /"(?:\\[tnrf"\\]|\\[0-7]{3}|[^"\\\r\n])*"/ ;
