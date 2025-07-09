" Vim filetype detection for Subunit streams
" Detect .subunit files
au BufRead,BufNewFile *.subunit set filetype=subunit

" Detect subunit v1 format by content
" au BufRead,BufNewFile * if getline(1) =~ '^\(test\|success\|failure\|error\|skip\|xfail\|uxsuccess\|progress\|tags\|time\):' | set filetype=subunit | endif
