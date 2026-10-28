"""Tests for fcgi_client.py, php_fastcgi_demo.py, fpm_pool_calc.py, wp_nginx_lint.py — চালানো: python3 -m unittest -v

php-cgi না থাকলে আসল FastCGI test skip হয় (Ubuntu: sudo apt install php-cgi)।
"""
from __future__ import annotations

import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fcgi_client as fc  # noqa: E402
import fpm_pool_calc as fp  # noqa: E402
import php_fastcgi_demo as demo  # noqa: E402
import wp_nginx_lint as wl  # noqa: E402


class ProtocolTest(unittest.TestCase):
    def test_record_layout_and_padding(self) -> None:
        rec = fc.record(fc.PARAMS, b"abc")
        version, rtype, rid, clen, pad = struct.unpack(">BBHHBx", rec[:8])
        self.assertEqual((version, rtype, rid, clen, pad), (1, 4, 1, 3, 5))
        self.assertEqual(len(rec) % 8, 0)                                         # ৮-byte alignment

    def test_name_value_lengths(self) -> None:
        self.assertEqual(fc.name_value(b"A", b"B"), b"\x01\x01AB")
        long = fc.name_value(b"K", b"v" * 200)
        self.assertEqual(long[1:5], struct.pack(">I", 200 | 0x80000000))          # ১২৮+ = ৪ byte, উঁচু bit set

    def test_params_like_nginx(self) -> None:
        p = fc.nginx_params("/srv/a.php", "/a.php?x=1", "/srv")
        self.assertEqual((p["SCRIPT_FILENAME"], p["QUERY_STRING"], p["SCRIPT_NAME"]), ("/srv/a.php", "x=1", "/a.php"))
        self.assertNotIn("SCRIPT_FILENAME", fc.nginx_params(None, "/a.php", "/srv"))


@unittest.skipIf(shutil.which("php-cgi") is None, "php-cgi not installed")
class RealPhpTest(unittest.TestCase):
    def test_three_classic_situations(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            results = dict(demo.run(demo.make_docroot(Path(d))))
        self.assertIn("p=1", results["fix_pathinfo=1  correct SCRIPT_FILENAME"])
        self.assertIn("No input file specified", results["fix_pathinfo=1  SCRIPT_FILENAME missing (fastcgi_params)"])
        self.assertIn("EXECUTED AS PHP", results["fix_pathinfo=1  /uploads/avatar.jpg/x.php (path-info trick)"])
        self.assertIn("404", results["fix_pathinfo=0  /uploads/avatar.jpg/x.php (path-info trick)"])


class PoolTest(unittest.TestCase):
    def test_calc(self) -> None:
        r = fp.calc(2048, 700, 60)
        self.assertEqual((r["pm.max_children"], r["pm.start_servers"]), (20, 5))
        with self.assertRaisesRegex(ValueError, "not enough"):
            fp.calc(512, 450, 60)


class LintTest(unittest.TestCase):
    def codes(self, name: str) -> set[str]:
        path = HERE / name
        return {f[2] for f in wl.lint(wl.nc.parse(path.read_text(encoding="utf-8"), str(path)))}

    def test_broken_and_good(self) -> None:
        self.assertEqual(self.codes("wordpress-broken.conf"),
                         {"php-no-file-check", "no-script-filename", "uploads-php-allowed", "dotfiles-allowed",
                          "upload-size", "no-front-controller"})
        self.assertEqual(self.codes("wordpress.conf"), set())

    def test_explicit_script_filename_is_fine(self) -> None:
        tree = wl.nc.parse("server { location ~ \\.php$ { try_files $uri =404; include fastcgi_params; "
                           "fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name; fastcgi_pass x; } }")
        self.assertNotIn("no-script-filename", {f[2] for f in wl.lint(tree)})


if __name__ == "__main__":
    unittest.main()
