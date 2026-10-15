# HMI format references

The clock-source generator is an independent implementation for the single
pinned Easy EU HMI. It does not embed or run the Nextion Editor or alter a
compiled TFT. Format references used during development:

- Nextion2Text at 7edf48558208dcf92ba8d9dd649677b06c1362db, by Max Zuidberg,
  MPL-2.0: https://github.com/MMMZZZZ/Nextion2Text . Its reader established the
  length-prefixed groups and component offsets relative to the 56-byte page header.
  No Nextion2Text source is vendored into this repository.
- Evan Severson's Nextion HMI research (MIT):
  https://github.com/eseverson/nextion-hmi/blob/main/findings/directory-checksum.md
  and findings/format-hmi.md, describing the CRC algorithms. Its writer examples
  are not used unchanged; their offset assumptions did not match the pinned Easy
  source. All checksums and resource preservation are validated on the actual file.

The following notice accompanies the CRC-method reference and any derived work:

MIT License

Copyright (c) 2026 Evan Severson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
