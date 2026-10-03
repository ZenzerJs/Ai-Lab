import unittest
try:
    from src.slugify import slugify
except ImportError:
    from slugify import slugify


class TestSlugify(unittest.TestCase):
    def test_basic_slug(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_custom_separator(self):
        self.assertEqual(slugify("Hello World", separator="_"), "hello_world")

    def test_multiple_spaces_and_hyphens(self):
        self.assertEqual(slugify("  hello   ---  world  "), "hello-world")

    def test_special_characters_removal(self):
        self.assertEqual(slugify("Hello, World! #2026 @AI"), "hello-world-2026-ai")

    def test_unicode_transliteration_default(self):
        # Accented characters converted to ASCII equivalents
        self.assertEqual(slugify("Crème brûlée"), "creme-brulee")

    def test_unicode_allowed(self):
        # Unicode characters preserved when allow_unicode=True
        self.assertEqual(slugify("你好 World", allow_unicode=True), "你好-world")
        self.assertEqual(slugify("Crème brûlée", allow_unicode=True), "crème-brûlée")

    def test_empty_and_whitespace(self):
        self.assertEqual(slugify(""), "")
        self.assertEqual(slugify("   "), "")

    def test_non_string_input(self):
        self.assertEqual(slugify(12345), "12345")


if __name__ == "__main__":
    unittest.main()
