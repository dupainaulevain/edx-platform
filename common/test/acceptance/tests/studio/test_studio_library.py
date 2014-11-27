"""
Acceptance tests for Content Libraries in Studio
"""

from .base_studio_test import StudioLibraryTest
from ...fixtures.course import XBlockFixtureDesc
from ...pages.studio.library import LibraryPage


class LibraryEditPageTest(StudioLibraryTest):
    """
    Test the functionality of the library edit page.
    """
    def setUp(self):  # pylint: disable=arguments-differ
        """
        Ensure a library exists and navigate to the library edit page.
        """
        super(LibraryEditPageTest, self).setUp(is_staff=True)
        self.lib_page = LibraryPage(self.browser, self.library_key)
        self.lib_page.visit()
        self.lib_page.wait_until_ready()

    def test_page_header(self):
        """
        Check that the library's name is displayed in the header and title.
        """
        self.assertIn(self.library_info['display_name'], self.lib_page.get_header_title())
        self.assertIn(self.library_info['display_name'], self.browser.title)

    def test_add_duplicate_delete_actions(self):
        """
        Test that we can add an HTML block, duplicate it, then delete the original.
        """
        self.assertEqual(len(self.lib_page.xblocks), 0)

        # Create a new block:
        self.lib_page.click_add_button("html", "Text")
        self.assertEqual(len(self.lib_page.xblocks), 1)
        first_block_id = self.lib_page.xblocks[0].locator

        # Duplicate the block:
        self.lib_page.click_duplicate_button(first_block_id)
        self.assertEqual(len(self.lib_page.xblocks), 2)
        second_block_id = self.lib_page.xblocks[1].locator
        self.assertNotEqual(first_block_id, second_block_id)

        # Delete the first block:
        self.lib_page.click_delete_button(first_block_id, confirm=True)
        self.assertEqual(len(self.lib_page.xblocks), 1)
        self.assertEqual(self.lib_page.xblocks[0].locator, second_block_id)

    def test_add_edit_xblock(self):
        """
        Test that we can add an XBlock, edit it, then see the resulting changes.
        """
        self.assertEqual(len(self.lib_page.xblocks), 0)
        # Create a new problem block:
        self.lib_page.click_add_button("problem", "Multiple Choice")
        self.assertEqual(len(self.lib_page.xblocks), 1)
        problem_block = self.lib_page.xblocks[0]
        # Edit it:
        problem_block.edit()
        problem_block.open_basic_tab()
        problem_block.set_codemirror_text(
            """
            >>Who is "Starbuck"?<<
             (x) Kara Thrace
             ( ) William Adama
             ( ) Laura Roslin
             ( ) Lee Adama
             ( ) Gaius Baltar
            """
        )
        problem_block.save_settings()
        # Check that the save worked:
        self.assertEqual(len(self.lib_page.xblocks), 1)
        problem_block = self.lib_page.xblocks[0]
        self.assertIn("Laura Roslin", problem_block.student_content)


class LibraryWithDepthTest(StudioLibraryTest):
    """
    Tests for a lbirary that has a hierarchy of content.
    """
    def setUp(self):  # pylint: disable=arguments-differ
        """
        Create a library with a content hierarchy, and navigate to the library
        edit page.
        """
        super(LibraryWithDepthTest, self).setUp(is_staff=True)
        self.lib_page = LibraryPage(self.browser, self.library_key)
        self.lib_page.visit()
        self.lib_page.wait_until_ready()

    def populate_library_fixture(self, library_fixture):
        """
        Define the blocks that will be in the library at first.
        """
        # self, category, display_name, data=None, metadata=None, grader_type=None, publish='make_public')
        library_fixture.add_children(
            XBlockFixtureDesc('html', "First Block", data="A boring HTML block."),
            XBlockFixtureDesc('vertical', "A block with two children").add_children(
                XBlockFixtureDesc('html', "First child of the vertical", data="Hello world."),
                XBlockFixtureDesc('html', "Second child of the vertical", data="Hello world."),
            )
        )

    def test_hierarchical_content(self):
        """
        Test that we can view the library with hierarchical content, and that
        any verticals in the library are shown collapsed, with a "View" link.
        The container page for library verticals has not yet been implemented
        so we do not test it.
        """
        self.assertEqual(len(self.lib_page.xblocks), 2)
        vert_block = self.lib_page.xblocks[1]
        self.assertTrue(vert_block.container_link_url)  # Check that it has a "View" link to the container page
        vert_block.edit()
        vert_block.save_settings()
        self.assertTrue(False)  # Screenshot
