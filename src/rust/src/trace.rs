//! Lightweight source-line tracking for Ago runtime tracebacks.
//!
//! The code generator emits `ago_set_line(N)` before each user statement, where
//! N is the 1-based line in the user's `.ago` file. On a panic (index out of
//! bounds, divide by zero, calling a non-function, ...), the installed hook
//! reports that line so the error points at Ago source rather than at the
//! generated Rust. A panic inside a prelude function keeps the caller's line,
//! since prelude statements don't update the tracker — which is exactly the line
//! the user can act on.

use std::cell::Cell;

thread_local! {
    static AGO_LINE: Cell<u32> = const { Cell::new(0) };
}

/// Record the Ago source line about to execute. Cheap (a thread-local set).
#[inline]
pub fn ago_set_line(line: u32) {
    AGO_LINE.with(|c| c.set(line));
}

/// The most recently recorded Ago source line (0 if none yet).
#[inline]
pub fn ago_current_line() -> u32 {
    AGO_LINE.with(|c| c.get())
}

/// Native integer divide / modulo, routed through a function so a literal
/// divisor of zero is a clean runtime panic (caught by the hook and mapped to
/// the Ago line) rather than rustc's compile-time `unconditional_panic` lint,
/// which would surface as an opaque "could not compile" error.
#[inline]
pub fn ago_div(a: i128, b: i128) -> i128 {
    a / b
}

#[inline]
pub fn ago_mod(a: i128, b: i128) -> i128 {
    a % b
}

/// Install a panic hook that prints a single machine-readable line the CLI can
/// turn into a clean Ago diagnostic, and suppresses the Rust backtrace.
///
/// Format: `__AGO_RT__<line>\t<message>`
pub fn ago_install_panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let msg = if let Some(s) = info.payload().downcast_ref::<&str>() {
            (*s).to_string()
        } else if let Some(s) = info.payload().downcast_ref::<String>() {
            s.clone()
        } else {
            "runtime error".to_string()
        };
        // Collapse any newlines so the marker stays on one line.
        let msg = msg.replace('\n', " ");
        eprintln!("__AGO_RT__{}\t{}", ago_current_line(), msg);
    }));
}
