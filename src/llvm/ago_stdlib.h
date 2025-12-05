/**
 * Ago Standard Library - Header File
 * 
 * Function declarations for the Ago runtime library.
 */

#ifndef AGO_STDLIB_H
#define AGO_STDLIB_H

#include <stdint.h>
#include <stdbool.h>

// ============================================================================
// Arithmetic Operations
// ============================================================================

int64_t ago_add(int64_t a, int64_t b);
int64_t ago_subtract(int64_t a, int64_t b);
int64_t ago_multiply(int64_t a, int64_t b);
int64_t ago_divide(int64_t a, int64_t b);
int64_t ago_modulo(int64_t a, int64_t b);

// ============================================================================
// Comparison Operations
// ============================================================================

bool ago_equal(int64_t a, int64_t b);
bool ago_not_equal(int64_t a, int64_t b);
bool ago_less_than(int64_t a, int64_t b);
bool ago_greater_than(int64_t a, int64_t b);
bool ago_less_equal(int64_t a, int64_t b);
bool ago_greater_equal(int64_t a, int64_t b);

// ============================================================================
// Logical Operations
// ============================================================================

bool ago_logical_and(bool a, bool b);
bool ago_logical_or(bool a, bool b);
bool ago_logical_not(bool a);

// ============================================================================
// I/O Operations
// ============================================================================

void ago_print_int(int64_t value);
void ago_print_float(double value);
void ago_print_bool(bool value);
void ago_print_string(const char* str);

// ============================================================================
// String Operations
// ============================================================================

char* ago_string_concat(const char* a, const char* b);
int64_t ago_string_length(const char* str);
char* ago_string_get(const char* str, int64_t index);

// ============================================================================
// List Operations
// ============================================================================

typedef struct {
    int64_t length;
    int64_t* data;
} AgoIntList;

typedef struct {
    int64_t length;
    double* data;
} AgoFloatList;

AgoIntList* ago_list_int_new(int64_t capacity);
int64_t ago_list_int_get(AgoIntList* list, int64_t index);
void ago_list_int_set(AgoIntList* list, int64_t index, int64_t value);
void ago_list_int_append(AgoIntList* list, int64_t value);
void ago_list_int_free(AgoIntList* list);

// ============================================================================
// Utility Functions
// ============================================================================

char* ago_read_line(void);
void ago_exit(int64_t code);
const char* ago_type_name(void* value);

#endif // AGO_STDLIB_H