# Chiyan motion optimization

User authorized autonomous implementation, validation and GitHub submission.

Keep Python/PyQt and the existing artwork. Improve complete-action playback,
frame timing, nonrepeating weighted selection, short horizontal wandering,
dragging, throwing and subtle landing squash. Reuse six-frame breathing and
the six existing complete keyframe actions. This does not generate continuous
video or modify Codex's built-in player. Credit the DSH reference; implement
algorithms independently without copying its source.

1. Test and implement a pure playback model and nonrepeating weighted chooser.
2. Test and implement bounded spring/throw physics and fresh release sampling.
3. Integrate into Qt, add full action assets, test actual Qt event paths and rendering.
4. Document, build and smoke-test the release executable, independently review,
   fix findings and submit to the user's GitHub repository.

Review focus: long timer gaps; rapid action interruptions; pause/resize/reset
during flight; drag-vs-click and double-click semantics; small/negative-origin
screens; missing asset handling and packaged resource paths.

Ledger: Baseline 4 tests passed. Managed worktree is outside the writable root;
implementation runs in this ignored staging directory, then verified files are
copied into the isolated managed worktree for commit. Unrelated wallpaper CSS
remains in the original checkout.

Progress:
- Playback and physics implemented; six existing complete clips and current
  breathing atlas copied byte-for-byte. No new generated artwork or video.
- Qt tests reproduce real click/double-click and drag events, rendering,
  completion, interruption alpha, placement, flight, resize, pause and pack faults.
- First full suite: 38 passing. Repeated transitions initially lost alpha;
  reproduced and fixed with preweighted additive premultiplied layers.
- Independent reviewer found optional duration integer overflow; regression
  reproduced and fixed. Also tested/fixed offscreen pause and custom menu entries.
- Final suite at implementation completion: 42 passing, including native window
  title discoverability. The packaged pet process was responsive in session 1;
  final rebuild includes the title for UI inspection.
- Real Qt preview rendered (429 frames). Final corrected EXE built successfully.
  Native smoke process was responsive; the Windows automation helper does not
  expose this transparent Qt.Tool window, so native input/screenshot verification
  is unavailable. Offscreen real-widget rendering and events passed.
- Copied final source, artwork and release into the managed worktree. Full
  worktree suite: 42 passing; diff whitespace check passed. GitHub submission follows.
