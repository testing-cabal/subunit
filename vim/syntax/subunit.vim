" Vim syntax file
" Language:     Subunit v1 test protocol
" Maintainer:   Jelmer Vernooĳ <jelmer@jelmer.uk>
" Last Change:  2025-07-09
" Version:      0.1

if exists("b:current_syntax")
  finish
endif

" Test directives
syn keyword subunitDirective test success failure error skip xfail uxsuccess
syn keyword subunitDirective progress tags time

" Test labels (after test directives, up to opening bracket if present)
syn match subunitTestLabel "\(test:\s*\)\@<=.\{-}\(\s*\[\)\@="
syn match subunitTestLabel "\(test:\s*\)\@<=.*$" contains=subunitDetails
syn match subunitTestLabel "\(success:\s*\)\@<=.\{-}\(\s*\[\)\@="
syn match subunitTestLabel "\(success:\s*\)\@<=.*$" contains=subunitDetails
syn match subunitTestLabel "\(failure:\s*\)\@<=.\{-}\(\s*\[\)\@="
syn match subunitTestLabel "\(failure:\s*\)\@<=.*$" contains=subunitDetails
syn match subunitTestLabel "\(error:\s*\)\@<=.\{-}\(\s*\[\)\@="
syn match subunitTestLabel "\(error:\s*\)\@<=.*$" contains=subunitDetails
syn match subunitTestLabel "\(skip:\s*\)\@<=.\{-}\(\s*\[\)\@="
syn match subunitTestLabel "\(skip:\s*\)\@<=.*$" contains=subunitDetails
syn match subunitTestLabel "\(xfail:\s*\)\@<=.\{-}\(\s*\[\)\@="
syn match subunitTestLabel "\(xfail:\s*\)\@<=.*$" contains=subunitDetails
syn match subunitTestLabel "\(uxsuccess:\s*\)\@<=.\{-}\(\s*\[\)\@="
syn match subunitTestLabel "\(uxsuccess:\s*\)\@<=.*$" contains=subunitDetails

" Progress indicators
syn match subunitProgress "progress:\s*[+-]\?\d\+"

" Tags
syn match subunitTag "tags:\s*.*$" contains=subunitTagList
syn match subunitTagList "\(tags:\s*\)\@<=.*$" contained

" Time stamps
syn match subunitTime "time:\s*\d\{4}-\d\{2}-\d\{2}\s\+\d\{2}:\d\{2}:\d\{2}Z\?"

" Bracketed sections for details (multiline)
" Extended descriptions can appear after test result directives
syn region subunitDetails start="\[" end="^\s*\]" fold contains=NONE

" MIME boundaries
syn match subunitMimeBoundary "^--[a-zA-Z0-9_-]\+--\?$"
syn match subunitMimeHeader "^Content-Type:.*$"

" Comments (if any line doesn't match known patterns)
syn match subunitComment "^#.*$"

" Define highlighting
hi def link subunitDirective    Keyword
hi def link subunitTestLabel    String
hi def link subunitProgress     Number
hi def link subunitTag          Special
hi def link subunitTagList      Identifier
hi def link subunitTime         Constant
hi def link subunitDetails      Comment
hi def link subunitMimeBoundary PreProc
hi def link subunitMimeHeader   Type
hi def link subunitComment      Comment

let b:current_syntax = "subunit"
