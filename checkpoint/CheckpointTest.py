#!/usr/bin/env python
#
# Copyright (C) 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from vts.runners.host import asserts
from vts.runners.host import base_test
from vts.runners.host import const
from vts.runners.host import test_runner


class VtsKernelCheckpointTest(base_test.BaseTestClass):

    _CHECKPOINTTESTFILE = "/data/local/tmp/checkpointtest"
    _ORIGINALVALUE = "original value"
    _MODIFIEDVALUE = "modified value"

    def getFstab(self):
        self.dut.adb.root()

        for prop in ["hardware", "hardware.platform"]:
            extension = self.dut.adb.shell("getprop ro.boot." + prop, no_except = True)
            extension = extension[const.STDOUT]
            if not extension:
                continue

            for filename in ["/odm/etc/fstab.", "/vendor/etc/fstab.", "/fstab."]:
                contents = self.dut.adb.shell("cat " + filename + extension, no_except = True)
                if contents[const.EXIT_CODE] != 0:
                    continue

                return contents[const.STDOUT]

        return ""

    def isCheckpoint(self):
        fstab = self.getFstab().splitlines()
        for line in fstab:
            parts = line.split()
            if len(parts) != 5: # fstab has five parts for each entry:
                                # [device-name] [mount-point] [type] [mount_flags] [fsmgr_flags]
                continue

            flags = parts[4]    # the fsmgr_flags field is the fifth one, thus index 4
            flags = flags.split(',')
            if any(flag.startswith("checkpoint=") for flag in flags):
                return True

        return False

    def setUpClass(self):
        self.dut = self.android_devices[0]
        self.shell = self.dut.shell
        self.isCheckpoint_ = self.isCheckpoint()

    def reboot(self):
        self.dut.reboot()
        self.dut.adb.root()

    def testRollback(self):
        if not self.isCheckpoint_:
            return

        # Create a file and initiate checkpoint
        self.dut.adb.root()
        self.dut.adb.shell("echo " + self._ORIGINALVALUE + " > " + self._CHECKPOINTTESTFILE)
        result = self.dut.adb.shell("vdc checkpoint startCheckpoint 1", no_except = True)
        asserts.assertEqual(result[const.EXIT_CODE], 1)
        self.reboot()

        # Modify the file but do not commit
        self.dut.adb.shell("echo " + self._MODIFIEDVALUE + " > " + self._CHECKPOINTTESTFILE)
        self.reboot()

        # Check the file is unchanged
        result = self.dut.adb.shell("cat " + self._CHECKPOINTTESTFILE)
        asserts.assertEqual(result.strip(), self._ORIGINALVALUE)

        # Clean up
        result = self.dut.adb.shell("vdc checkpoint commitChanges", no_except = True)
        asserts.assertEqual(result[const.EXIT_CODE], 1)
        self.reboot()
        self.dut.adb.shell("rm " + self._CHECKPOINTTESTFILE)

    def testCommit(self):
        if not self.isCheckpoint_:
            return

        # Create a file and initiate checkpoint
        self.dut.adb.root()
        self.dut.adb.shell("echo " + self._ORIGINALVALUE + " > " + self._CHECKPOINTTESTFILE)
        result = self.dut.adb.shell("vdc checkpoint startCheckpoint 1", no_except = True)
        asserts.assertEqual(result[const.EXIT_CODE], 1)
        self.reboot()

        # Modify the file and commit the checkpoint
        self.dut.adb.shell("echo " + self._MODIFIEDVALUE + " > " + self._CHECKPOINTTESTFILE)
        result = self.dut.adb.shell("vdc checkpoint commitChanges", no_except = True)
        asserts.assertEqual(result[const.EXIT_CODE], 1)
        self.reboot()

        # Check file has changed
        result = self.dut.adb.shell("cat " + self._CHECKPOINTTESTFILE)
        asserts.assertEqual(result.strip(), self._MODIFIEDVALUE)

        # Clean up
        self.dut.adb.shell("rm " + self._CHECKPOINTTESTFILE)

if __name__ == "__main__":
    test_runner.main()