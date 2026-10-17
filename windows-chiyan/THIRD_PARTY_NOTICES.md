# References and artwork provenance

Motion scheduling, action-boundary transitions, and the separation of pointer
physics from rendered character actions were studied in PC2005-cloud/dsh-pet:
https://github.com/PC2005-cloud/dsh-pet
Reference revision: 6c5f04321be050525b5cbb7bb8ee5f53e89deb6f (MIT license).

This implementation independently uses Python/PyQt; no DSH source code,
character artwork, videos, sound or fonts are included. The reference's video
production workflow is not implemented or represented as completed here.

The Chiyan artwork was generated earlier for this repository. Core atlas:
animations/idle-breath-2026-10-16/chiyan-native-breath.png. Additional action
frames: animations/idle-six/{hair,collar,sleep,stretch,typing,peek}/clean/.
prepare_assets.py copies these existing files without image edits; their
generation history remains in the corresponding source directories.

PyQt5 and PyInstaller remain the existing runtime/build dependencies, governed
by their respective distributions' licenses. Pillow is a developer-only preview
dependency and is not imported by the runtime application.
