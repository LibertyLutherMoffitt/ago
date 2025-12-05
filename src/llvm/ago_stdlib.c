/**
 * Ago Standard Library - C Implementation
 * 
 * This file implements the core runtime functions for the Ago programming language.
 * It is compiled to LLVM IR and linked with generated Ago code.
 */

#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

// ============================================================================
// Arithmetic Operations
// ============================================================================

int64_t ago_add(int64_t a, int64_t b) {
    return a + b;
}

int64_t ago_subtract(int64_t a, int64_t b) {
    return a - b;
}

int64_t ago_multiply(int64_t a, int64_t b) {
    return a * b;
}

int64_t ago_divide(int64_t a, int64_t b) {
    if (b == 0) {
        fprintf(stderr, "Error: Division by zero\n");
        exit(1);
    }
    return a / b;
}

int64_t ago_modulo(int64_t a, int64_t b) {
    if (b == 0) {
        fprintf(stderr, "Error: Modulo by zero\n");
        exit(1);
    }
    return a % b;
}

// ============================================================================
// Comparison Operations
// ============================================================================

bool ago_equal(int64_t a, int64_t b) {
    return a == b;
}

bool ago_not_equal(int64_t a, int64_t b) {
    return a != b;
}

bool ago_less_than(int64_t a, int64_t b) {
    return a < b;
}

bool ago_greater_than(int64_t a, int64_t b) {
    return a > b;
}

bool ago_less_equal(int64_t a, int64_t b) {
    return a <= b;
}

bool ago_greater_equal(int64_t a, int64_t b) {
    return a >= b;
}

// ============================================================================
// Logical Operations
// ============================================================================

bool ago_logical_and(bool a, bool b) {
    return a && b;
}

bool ago_logical_or(bool a, bool b) {
    return a || b;
}

bool ago_logical_not(bool a) {
    return !a;
}

// ============================================================================
// I/O Operations
// ============================================================================

void ago_print_int(int64_t value) {
    printf("%lld\n", (long long)value);
}

void ago_print_float(double value) {
    printf("%f\n", value);
}

void ago_print_bool(bool value) {
    printf("%s\n", value ? "verum" : "falsus");
}

void ago_print_string(const char* str) {
    if (str != NULL) {
        printf("%s\n", str);
    }
}

// ============================================================================
// String Operations
// ============================================================================

/**
 * Concatenate two strings and return a new allocated string.
 * Caller is responsible for freeing the result.
 */
char* ago_string_concat(const char* a, const char* b) {
    if (a == NULL) a = "";
    if (b == NULL) b = "";
    
    size_t len_a = strlen(a);
    size_t len_b = strlen(b);
    size_t total_len = len_a + len_b;
    
    char* result = (char*)malloc(total_len + 1);
    if (result == NULL) {
        fprintf(stderr, "Error: Memory allocation failed\n");
        exit(1);
    }
    
    memcpy(result, a, len_a);
    memcpy(result + len_a, b, len_b);
    result[total_len] = '\0';
    
    return result;
}

/**
 * Get the length of a string.
 */
int64_t ago_string_length(const char* str) {
    if (str == NULL) return 0;
    return (int64_t)strlen(str);
}

/**
 * Get a character from a string at the given index.
 * Returns a new single-character string.
 */
char* ago_string_get(const char* str, int64_t index) {
    if (str == NULL) {
        fprintf(stderr, "Error: Cannot index null string\n");
        exit(1);
    }
    
    int64_t len = (int64_t)strlen(str);
    if (index < 0 || index >= len) {
        fprintf(stderr, "Error: String index out of bounds: %lld (length: %lld)\n", 
                (long long)index, (long long)len);
        exit(1);
    }
    
    char* result = (char*)malloc(2);
    if (result == NULL) {
        fprintf(stderr, "Error: Memory allocation failed\n");
        exit(1);
    }
    
    result[0] = str[index];
    result[1] = '\0';
    
    return result;
}

// ============================================================================
// List Operations
// ============================================================================

/**
 * List structure: {length, data_pointer}
 * For int lists: {int64_t length, int64_t* data}
 */

typedef struct {
    int64_t length;
    int64_t* data;
} AgoIntList;

typedef struct {
    int64_t length;
    double* data;
} AgoFloatList;

/**
 * Create a new integer list with the given capacity.
 */
AgoIntList* ago_list_int_new(int64_t capacity) {
    AgoIntList* list = (AgoIntList*)malloc(sizeof(AgoIntList));
    if (list == NULL) {
        fprintf(stderr, "Error: Memory allocation failed\n");
        exit(1);
    }
    
    list->length = 0;
    list->data = (int64_t*)malloc(capacity * sizeof(int64_t));
    if (list->data == NULL) {
        free(list);
        fprintf(stderr, "Error: Memory allocation failed\n");
        exit(1);
    }
    
    return list;
}

/**
 * Get an element from an integer list.
 */
int64_t ago_list_int_get(AgoIntList* list, int64_t index) {
    if (list == NULL) {
        fprintf(stderr, "Error: Cannot index null list\n");
        exit(1);
    }
    
    if (index < 0 || index >= list->length) {
        fprintf(stderr, "Error: List index out of bounds: %lld (length: %lld)\n",
                (long long)index, (long long)list->length);
        exit(1);
    }
    
    return list->data[index];
}

/**
 * Set an element in an integer list.
 */
void ago_list_int_set(AgoIntList* list, int64_t index, int64_t value) {
    if (list == NULL) {
        fprintf(stderr, "Error: Cannot index null list\n");
        exit(1);
    }
    
    if (index < 0 || index >= list->length) {
        fprintf(stderr, "Error: List index out of bounds: %lld (length: %lld)\n",
                (long long)index, (long long)list->length);
        exit(1);
    }
    
    list->data[index] = value;
}

/**
 * Append an element to an integer list.
 * Note: This is a simplified version that doesn't handle capacity growth.
 */
void ago_list_int_append(AgoIntList* list, int64_t value) {
    if (list == NULL) {
        fprintf(stderr, "Error: Cannot append to null list\n");
        exit(1);
    }
    
    // Reallocate with more space
    int64_t new_capacity = list->length + 1;
    int64_t* new_data = (int64_t*)realloc(list->data, new_capacity * sizeof(int64_t));
    if (new_data == NULL) {
        fprintf(stderr, "Error: Memory allocation failed\n");
        exit(1);
    }
    
    list->data = new_data;
    list->data[list->length] = value;
    list->length++;
}

/**
 * Free an integer list.
 */
void ago_list_int_free(AgoIntList* list) {
    if (list != NULL) {
        if (list->data != NULL) {
            free(list->data);
        }
        free(list);
    }
}

// ============================================================================
// Struct/Map Operations (Simplified)
// ============================================================================

/**
 * For now, structs are represented as opaque pointers.
 * A full implementation would use a hash table.
 */

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Read a line from stdin.
 */
char* ago_read_line(void) {
    char* line = NULL;
    size_t len = 0;
    ssize_t read = getline(&line, &len, stdin);
    
    if (read == -1) {
        if (line != NULL) free(line);
        return NULL;
    }
    
    // Remove trailing newline
    if (read > 0 && line[read - 1] == '\n') {
        line[read - 1] = '\0';
    }
    
    return line;
}

/**
 * Exit the program with the given code.
 */
void ago_exit(int64_t code) {
    exit((int)code);
}

/**
 * Get the type name of a value (placeholder).
 */
const char* ago_type_name(void* value) {
    // This would need runtime type information
    (void)value;  // Suppress unused parameter warning
    return "unknown";
}