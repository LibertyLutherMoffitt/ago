; ModuleID = 'ago_program'
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

declare i8* @malloc(i64)
declare void @free(i8*)
declare i64 @ago_add(i64, i64)
declare i64 @ago_subtract(i64, i64)
declare i64 @ago_multiply(i64, i64)
declare i64 @ago_divide(i64, i64)
declare i64 @ago_modulo(i64, i64)
declare i1 @ago_equal(i64, i64)
declare i1 @ago_not_equal(i64, i64)
declare i1 @ago_less_than(i64, i64)
declare i1 @ago_greater_than(i64, i64)
declare i1 @ago_less_equal(i64, i64)
declare i1 @ago_greater_equal(i64, i64)
declare i1 @ago_logical_and(i1, i1)
declare i1 @ago_logical_or(i1, i1)
declare i1 @ago_logical_not(i1)
declare i8* @ago_string_concat(i8*, i8*)
declare void @ago_print_int(i64)
declare void @ago_print_string(i8*)


define i64 @scribia(i64 %xa) {
  %0 = call i64 @ago_add(i64 %xa, i64 1)
  ret i64 %0
}

define i32 @main() {
  %xa = alloca i64
  store i64 5, i64* %xa
  %1 = load i64, i64* %xa
  call void @ago_print_int(i64 %1)
  ret i32 0
}