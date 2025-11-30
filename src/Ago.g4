@@grammar :: Ago
@@whitespace :: /[ \t]+/
@@comments :: /(?m)#([^\n]*?)$/
@@eol_comments :: /(?m)#([^\n]*?)$/
@@left_recursion :: True

@@keyword :: aluid falsus frio id pergo omitto redeo
@@keyword :: si est pro dum inanis tunc verum
@@keyword :: et vel non des in inporto

principio
    =
    [ nl ]
    sub_principio
    { nl }
    { sub_principio { nl } }
    [ nl ]
    $
    ;

sub_principio
    =
    | statement
    | method_decl
    | nl
    ;

statement
    =
    | declaration_stmt
    | reassignment_stmt
    | if_stmt:if_stmt
    | for_stmt:for_stmt
    | while_stmt:while_stmt
    | call:call_stmt
    | PASS
    | BREAK
    | CONTINUE
    | return_stmt:(RETURN value:expression)
    ;

lambda_decl
    = 
    DEF [ LPAREN [ params:expression_list ] RPAREN ]
    body:block
    ;


method_decl
    =
    DEF name:identifier
        LPAREN [ params:expression_list ] RPAREN
        body:block
    ;


declaration_stmt
    =
    name:identifier ASSIGNMENT_OP value:expression
    ;


reassignment_stmt
    =
    target:identifier [ index:indexing ] REASSIGNMENT_OP value:expression
    ;

indexing
    =
    indexes:{ LBRACKET expr:expression RBRACKET }+
    ;

else_fragment
    = 
    ELSE else_body:block
    ;


if_stmt
    =
    IF cond:expression then:block
        elifs:{ [nl] ELSE elif_cond:expression elif_body:block }*
        [ [nl] else_frag:else_fragment ]
    ;

block
    =
    LBRACE
        [ nl ]
        [ stmts:statement_list ]
        [ nl ]
    RBRACE
    ;

statement_list
    =
    first:statement
    rest:{ { nl }+ statement }*
    ;

while_stmt
    =
    WHILE cond:expression body:block
    ;

for_stmt
    =
    FOR iterator:identifier IN iterable:expression body:block
    ;

# --- CALLS ---

call_stmt
    =
    | recv:literal_item PERIOD first:nodotcall_stmt chain:{ PERIOD more:nodotcall_stmt }*
    | [ recv:(receiver:item) PERIOD ] first:(nodotcall_stmt | identifier) chain:{ PERIOD more:nodotcall_stmt }*
    ;

literal_item
    =
    | str:STR_LIT
    | float:FLOATLIT
    | int:INTLIT
    | roman:ROMAN_NUMERAL
    | TRUE
    | FALSE
    | NULL
    | paren:(LPAREN expr:expression RPAREN)
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
    | left:pd op:(EQ | NE | GE | LE | LT | GT | IS | IN) right:pd
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
    | list:list
    | value:item
    | mapstruct:mapstruct
    ;

list
    = 
    LBRACKET { item COMMA }* [ item ] RBRACKET
    ;


mapstruct
    = 
    LBRACE [nl] [mapcontent] [nl] RBRACE
    ;

mapcontent
    =
    | [nl] (STR_LIT | identifier) COLON item COMMA [nl] [mapcontent]
    | [nl] (STR_LIT | identifier) COLON item [nl]
    ;

item
    =
    | paren:(LPAREN expr:expression RPAREN)
    | mchain:(
        base:item
        chain:{ PERIOD method:nodotcall_stmt }+
      ) 
    | call:nodotcall_stmt
    | mapstruct
    | indexed:(identifier idx:indexing)
    | struct_indexed:(
        base:item
        chain:{ PERIOD sub_item:(identifier | STR_LIT)}+
    )
    | lambda_decl
    | roman:ROMAN_NUMERAL
    | id:identifier
    | str:STR_LIT
    | float:FLOATLIT
    | int:INTLIT
    | TRUE
    | FALSE
    | NULL
    | IT
    ;

nl = { CR }+ ;

# ---------- lexical rules (tokens) ----------

ROMAN_NUMERAL = /[MCDLXIV]+/ ;

@name
identifier = /[A-Za-z_][A-Za-z_0-9]*/ ;
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
NE = '!=' ;

ASSIGNMENT_OP   = ':=' ;
REASSIGNMENT_OP = '=' ;

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
NULL    = 'inanis' ;
TRUE    = 'verum' ;
AND     = 'et' ;
OR      = 'vel' ;
NOT     = 'non' ;
DEF     = 'des' ;
IN      = 'in' ;
IMPORT  = 'inporto' ;

COMMA     = ',' ;
COLON     = ':' ;
SEMICOLON = ';' ;
PERIOD    = '.' ;

CR = /\r?\n/ ;

STR_LIT = /"(?:\\[tnrf"\\]|\\[0-7]{3}|[^"\\\r\n])*"/ ;
