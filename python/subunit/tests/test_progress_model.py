#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2009  Robert Collins <robertc@robertcollins.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import unittest

import subunit
from subunit.progress_model import ProgressModel


class TestProgressModel(unittest.TestCase):

    def assertProgressSummary(self, pos, total, progress):
        """Assert that a progress model has reached a particular point."""
        self.assertEqual(pos, progress.pos())
        self.assertEqual(total, progress.width())

    def test_new_progress_0_0(self):
        progress = ProgressModel()
        self.assertProgressSummary(0, 0, progress)

    def test_advance_0_0(self):
        progress = ProgressModel()
        progress.advance()
        self.assertProgressSummary(1, 0, progress)

    def test_advance_1_0(self):
        progress = ProgressModel()
        progress.advance()
        self.assertProgressSummary(1, 0, progress)

    def test_set_width_absolute(self):
        progress = ProgressModel()
        progress.set_width(10)
        self.assertProgressSummary(0, 10, progress)

    def test_set_width_absolute_preserves_pos(self):
        progress = ProgressModel()
        progress.advance()
        progress.set_width(2)
        self.assertProgressSummary(1, 2, progress)

    def test_adjust_width(self):
        progress = ProgressModel()
        progress.adjust_width(10)
        self.assertProgressSummary(0, 10, progress)
        progress.adjust_width(-10)
        self.assertProgressSummary(0, 0, progress)

    def test_adjust_width_preserves_pos(self):
        progress = ProgressModel()
        progress.advance()
        progress.adjust_width(10)
        self.assertProgressSummary(1, 10, progress)
        progress.adjust_width(-10)
        self.assertProgressSummary(1, 0, progress)

    def test_push_preserves_progress(self):
        progress = ProgressModel()
        progress.adjust_width(3)
        progress.advance()
        progress.push()
        self.assertProgressSummary(1, 3, progress)

    def test_advance_advances_substack(self):
        progress = ProgressModel()
        progress.adjust_width(3)
        progress.advance()
        progress.push()
        progress.adjust_width(1)
        progress.advance()
        self.assertProgressSummary(2, 3, progress)

    def test_adjust_width_adjusts_substack(self):
        progress = ProgressModel()
        progress.adjust_width(3)
        progress.advance()
        progress.push()
        progress.adjust_width(2)
        progress.advance()
        self.assertProgressSummary(3, 6, progress)

    def test_set_width_adjusts_substack(self):
        progress = ProgressModel()
        progress.adjust_width(3)
        progress.advance()
        progress.push()
        progress.set_width(2)
        progress.advance()
        self.assertProgressSummary(3, 6, progress)

    def test_pop_restores_progress(self):
        progress = ProgressModel()
        progress.adjust_width(3)
        progress.advance()
        progress.push()
        progress.adjust_width(1)
        progress.advance()
        progress.pop()
        self.assertProgressSummary(1, 3, progress)


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result
