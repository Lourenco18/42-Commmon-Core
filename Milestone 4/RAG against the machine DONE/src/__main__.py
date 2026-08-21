"""Compatibility entry point.

The actual implementation lives in the `student` package
(src/student/), and is normally invoked as `python -m student ...`.

The official 42 School evaluation sheet and exam scripts
(exams/scripts/*.sh) default to `python -m src ...` (with
`--module-name` available to override it). This thin shim lets the
project be invoked either way without duplicating any logic: it
simply forwards to `student.__main__.main`.
"""
from student.__main__ import main

if __name__ == '__main__':
    main()
