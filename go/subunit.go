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

// Package subunit provides a writer of the Subunit v2 protocol.
package subunit

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"hash/crc32"
	"io"
	"time"
)

// ErrPacketLen represents an unhandled packet length error
type ErrPacketLen struct {
	Length int
}

func (e *ErrPacketLen) Error() string {
	return fmt.Sprintf("packet too big (%d bytes)", e.Length)
}

// ErrNumber represents an error for a number that is over the size
type ErrNumber struct {
	Number int
}

func (e *ErrNumber) Error() string {
	return fmt.Sprintf("number too big (%d)", e.Number)
}

const (
	signature byte = 0xb3
	// Flags high byte
	version          byte = 0x2
	testIDPresent    byte = 0x8
	timestampPresent byte = 0x2
	// Flags low byte
	fileContentPresent byte = 0x40
	mimePresent        byte = 0x20
)

var status = map[string]byte{
	"exists":     0x1,
	"inprogress": 0x2,
	"success":    0x3,
	"uxsuccess":  0x4,
	"skip":       0x5,
	"fail":       0x6,
	"xfail":      0x7,
}

func makeLen(baseLen int) (length int, err error) {
	length = baseLen + 4 // Add the length of the CRC32.
	// We need to take into account the variable length of the length field itself.
	switch {
	case length <= 62:
		// Fits in one byte.
		length++
	case length <= 16381:
		// Fits in two bytes.
		length += 2
	case length <= 4194300:
		// Fits in three bytes.
		length += 3
	default:
		err = &ErrPacketLen{length}
	}

	return length, err
}

// StreamResultToBytes is an implementation of the StreamResult API that converts calls to bytes.
type StreamResultToBytes struct {
	Output io.Writer
}

// Event is a status or a file attachment event.
type Event struct {
	TestID    string
	Status    string
	Timestamp time.Time
	FileName  string
	FileBytes []byte
	MIME      string
}

type packetPart struct {
	bytes []byte
	err   error
}

func (e *Event) write(writer io.Writer) error {
	// PACKET := SIGNATURE FLAGS PACKET_LENGTH TIMESTAMP? TESTID? TAGS? MIME? FILECONTENT?
	//           ROUTING_CODE? CRC32

	flagsChan := make(chan []byte)
	go e.makeFlags(flagsChan)

	timestampChan := make(chan packetPart)
	go e.makeTimestamp(timestampChan)

	idChan := make(chan packetPart)
	go e.makeTestID(idChan)

	mimeChan := make(chan packetPart)
	go e.makeMIME(mimeChan)

	fileContentChan := make(chan packetPart)
	go e.makeFileContent(fileContentChan)

	// We construct a temporary buffer because we won't know the length until it's finished.
	// Then we insert the length.
	var bTemp bytes.Buffer
	bTemp.WriteByte(signature)
	bTemp.Write(<-flagsChan)
	for _, part := range []packetPart{<-timestampChan, <-idChan, <-mimeChan, <-fileContentChan} {
		if part.err != nil {
			return part.err
		}
		bTemp.Write(part.bytes)
	}

	length, err := makeLen(bTemp.Len())
	if err != nil {
		return err
	}
	// Insert the length.
	var b bytes.Buffer
	b.Write(bTemp.Next(3)) // signature (1 byte) and flags (2 bytes)
	writeNumber(&b, length)
	b.Write(bTemp.Next(bTemp.Len()))

	// Add the CRC32
	crc := crc32.ChecksumIEEE(b.Bytes())
	binary.Write(&b, binary.BigEndian, crc)

	_, err = writer.Write(b.Bytes())
	return err
}

func (e *Event) makeFlags(c chan<- []byte) {
	flags := make([]byte, 2, 2)
	flags[0] = version << 4
	if e.TestID != "" {
		flags[0] = flags[0] | testIDPresent
	}
	if !e.Timestamp.IsZero() {
		flags[0] = flags[0] | timestampPresent
	}
	if e.FileName != "" {
		flags[1] = flags[1] | fileContentPresent
	}
	if e.MIME != "" {
		flags[1] = flags[1] | mimePresent
	}
	flags[1] = flags[1] | status[e.Status]
	c <- flags
}

func (e *Event) makeTestID(c chan<- packetPart) {
	var testID bytes.Buffer
	var err error
	if e.TestID != "" {
		err = writeUTF8(&testID, e.TestID)
	}
	c <- packetPart{testID.Bytes(), err}
}

func (e *Event) makeTimestamp(c chan<- packetPart) {
	var timestamp bytes.Buffer
	var err error
	if !e.Timestamp.IsZero() {
		err = binary.Write(&timestamp, binary.BigEndian, uint32(e.Timestamp.Unix()))
		if err == nil {
			err = writeNumber(&timestamp, int(e.Timestamp.UnixNano()%1000000000))
		}
	}
	c <- packetPart{timestamp.Bytes(), err}
}

func (e *Event) makeMIME(c chan<- packetPart) {
	var mime bytes.Buffer
	var err error
	if e.MIME != "" {
		err = writeUTF8(&mime, e.MIME)
	}
	c <- packetPart{mime.Bytes(), err}
}

func (e *Event) makeFileContent(c chan<- packetPart) {
	var fileContent bytes.Buffer
	var err error
	if e.FileName != "" {
		err = writeUTF8(&fileContent, e.FileName)
		if err == nil {
			err = writeNumber(&fileContent, len(e.FileBytes))
		}
		if err == nil {
			_, err = fileContent.Write(e.FileBytes)
		}
	}
	c <- packetPart{fileContent.Bytes(), err}
}

func writeUTF8(b io.Writer, s string) error {
	err := writeNumber(b, len(s))
	if err != nil {
		return err
	}
	_, err = io.WriteString(b, s)
	return err
}

func writeNumber(b io.Writer, num int) (err error) {
	// The first two bits encode the size:
	// 00 = 1 byte
	// 01 = 2 bytes
	// 10 = 3 bytes
	// 11 = 4 bytes
	switch {
	case num < 64: // 2^(8-2)
		// Fits in one byte.
		binary.Write(b, binary.BigEndian, uint8(num))
	case num < 16384: // 2^(16-2)
		// Fits in two bytes.
		binary.Write(b, binary.BigEndian, uint16(num|0x4000)) // Set the size to 01.
	case num < 4194304: // 2^(24-2)
		// Fits in three bytes.
		// Drop the two least significant bytes and set the size to 10.
		binary.Write(b, binary.BigEndian, uint8((num>>16)|0x80))
		// Drop the two most significant bytes.
		binary.Write(b, binary.BigEndian, uint16(num&0xffff))
	case num < 1073741824: // 2^(32-2):
		// Fits in four bytes.
		// Set the size to 11.
		binary.Write(b, binary.BigEndian, uint32(num|0xc0000000))
	default:
		err = &ErrNumber{num}
	}

	return err
}

// Status informs the result about a test status.
func (s *StreamResultToBytes) Status(e Event) error {
	return e.write(s.Output)
}
