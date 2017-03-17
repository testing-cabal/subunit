// -*- Mode: Go; indent-tabs-mode: t -*-

/*
 * Copyright (c) 2015 Canonical Ltd
 *
 * Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
 * license at the users choice. A copy of both licenses are available in the
 * project source as Apache-2.0 and BSD. You may not use this file except in
 * compliance with one of these two licences.
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * license you chose for the specific language governing permissions and
 * limitations under that license.
 *
 */

package subunit_test

import (
	"testing"

	check "gopkg.in/check.v1"
)

// Hook up go check into the "go test" runner.
func Test(t *testing.T) { check.TestingT(t) }
