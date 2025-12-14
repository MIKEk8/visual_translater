# Implementation Plan: FR-4 - Intelligent Hotkey System with Time-Based Detection

**Feature:** Alt+A Smart Key with Priority-Based Translation  
**Priority:** P0 (Critical)  
**Target:** Windows 10/11 with Rust + Tauri + React  
**Date:** 2025-09-30

## Context

Revolutionary single-key hotkey system:
- Quick press (<1s): Smart translation with 5-source priority
- Long press (>=1s): Animated context menu with 6 actions

Current state: Partial Rust implementation (640 lines), full frontend hooks, no Windows API integration yet.

## Impacted Modules

### Backend
1. src-tauri/services/intelligent_hotkey.rs - Complete Windows API integration
2. src-tauri/commands/mod.rs - Add 7 Tauri commands
3. src-tauri/main.rs - Initialize manager on startup
4. src-tauri/Cargo.toml - Add clipboard-win, arboard, winapi dependencies

### Frontend
5. src/hooks/useHotkeys.ts - ALREADY COMPLETE
6. src/components/ContextMenu.tsx - ALREADY COMPLETE
7. src/App.tsx - Wire hooks and handle callbacks

## API/Contracts

### Commands
- initialize_intelligent_hotkey() -> Result<()>
- get_hotkey_performance_stats() -> HotkeyPerformanceStats
- update_quick_press_threshold(threshold_ms: u64)
- get_previous_areas(limit: usize) -> Vec<PreviousArea>
- clear_previous_areas()
- get_context_menu_items() -> Vec<ContextMenuItem>
- execute_context_action(action: String)

### Events (Backend to Frontend)
- hotkey-long-press: Show context menu
- smart-translation-request: Execute translation with source priority
- start-screen-selection: Launch area selector UI

### Invariants
1. Timing accuracy: ±50ms of 1000ms threshold
2. Priority order: 1→5 strictly (SelectedText → ClipboardText → ClipboardImage → PreviousArea → NewSelection)
3. Memory safety: Max 10 previous areas
4. Thread safety: Arc<Mutex<T>> for all state
5. Cleanup: Drop trait unregisters hotkeys

## Test Plan

### Unit Tests (6 tests in intelligent_hotkey.rs)
- test_priority_order_correctness
- test_timing_threshold_accuracy  
- test_previous_area_persistence
- test_stats_tracking
- test_clipboard_detection
- test_threshold_update

### Integration Tests (3 tests, new file)
- test_end_to_end_quick_press_workflow
- test_end_to_end_long_press_workflow
- test_hotkey_registration_failure

### Manual Testing (18 critical tests)
- 5 quick press priority tests
- 4 long press context menu tests
- 3 edge case tests
- 2 performance tests (stopwatch + memory monitor)

## Steps

### Phase 1: Backend Core (Days 1-2)
1. Add dependencies: clipboard-win, arboard, winapi
2. Implement real clipboard access (replace mocks)
3. Implement selected text detection (Ctrl+C simulation)
4. Add previous area persistence (JSON file)
5. Wire screenshot capture integration

### Phase 2: Tauri Commands (Day 3)
6. Implement 7 Tauri commands in commands/mod.rs
7. Update AppState with hotkey_manager field
8. Register commands in main.rs

### Phase 3: Frontend Integration (Day 4)
9. Integrate useHotkeys in App.tsx
10. Wire ContextMenu component
11. Add translation request handler

### Phase 4: Testing (Day 5)
12. Write 6 unit tests
13. Write 3 integration tests  
14. Execute 18 manual test cases
15. Performance validation (< 10ms, < 50MB)

### Phase 5: Documentation (Day 6)
16. Update module passport
17. Add usage documentation
18. Code review and cleanup

## Risks & Rollback

### Risks
1. Windows API compatibility - Mitigation: Graceful fallback
2. Hotkey conflicts - Mitigation: Allow key customization
3. Timing precision on slow systems - Mitigation: Configurable threshold
4. Clipboard race conditions - Mitigation: Retry logic
5. Memory leaks - Mitigation: Bounded channels, timeouts

### Rollback Strategy
- Immediate: Config flag to disable, fall back to simple hotkeys
- Partial: Keep context menu, disable priority system
- Full: Revert to separate hotkeys (Alt+C, Alt+Q, etc.)

### Success Criteria
- All tests passing (15+ unit, 3+ integration, 18/18 manual)
- Performance: <10ms response (measured)
- Memory: <50MB stable after 1 hour
- No crashes in 2-hour stress test
- Code review approved

## Metrics (NOT MEASURED - TARGETS ONLY)

Following CLAUDE.md standards, these are TARGETS:
- Performance: <10ms response (from REQUIREMENTS.md)
- Code: ~500 lines new, ~300 lines modified
- Tests: ~400 lines
- To verify: Build release + manual timing

## Dependencies

Must be complete:
- FR-1 Screenshot Engine (check rust_screenshot_engine.yml)
- FR-2 OCR Engine (check rust_ocr_engine.yml) 
- FR-3 Translation Service (check rust_translation_service.yml)

External deps:
- global-hotkey = "0.4" (PRESENT)
- clipboard-win = "5.0" (TO ADD)
- arboard = "3.3" (TO ADD)
- winapi = "0.3" (TO ADD)

## Next Actions

1. Validate prerequisites (FR-1, FR-2, FR-3)
2. Create branch: git checkout -b feature/fr4-intelligent-hotkey
3. Start Phase 1: Add dependencies
4. Daily commits after each phase
5. Continuous testing: cargo test

**Timeline:** 6 days (40 hours)  
**Complexity:** High  
**Risk:** Medium  

**Status:** ✅ Complete and Ready  
**Reviewed By:** Software Architect Agent  
**Next Review:** After Phase 2
