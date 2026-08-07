//! The shim's whole job is that `use gcc_core::…` still resolves and still decides the
//! same way. A shim that compiles but re-exports nothing useful would look fine in CI and
//! break on the first real dependent, so this imports through the OLD path and asserts a
//! decision, rather than merely asserting that the crate builds.

use gcc_core::{Config, ControllerState, HomeostaticLoop, Posture, Telemetry};

#[test]
fn old_path_still_resolves_and_still_decides() {
    let loop_ = HomeostaticLoop::new(Config::default());
    let tel = Telemetry::new(0.1, 0.5, 0.0).expect("benign telemetry is in range");
    let decision = loop_.update(ControllerState::default(), tel);
    assert_eq!(
        decision.posture,
        Posture::Default,
        "benign telemetry must still pass through untouched via the deprecated path"
    );
}

#[test]
fn the_numeric_boundary_survives_the_re_export() {
    // The boundary is the product. If the shim somehow widened it, the token-free
    // property would be weaker through the old name than the new one.
    assert!(Telemetry::new(f64::NAN, 0.0, 0.0).is_err(), "NaN must be rejected");
    assert!(Telemetry::new(f64::INFINITY, 0.0, 0.0).is_err(), "inf must be rejected");
    assert!(Telemetry::new(2.0, 0.0, 0.0).is_err(), "out-of-range must be rejected");
}
