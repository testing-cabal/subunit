# Subunit Vim Syntax Highlighting

This directory contains Vim syntax highlighting for Subunit v1 test protocol streams.

## Installation

### Option 1: Manual Installation

Copy the files to your Vim configuration directory:

```bash
cp -r syntax ~/.vim/
cp -r ftdetect ~/.vim/
```

### Option 2: Using a Plugin Manager

If you use a Vim plugin manager like vim-plug, add to your `.vimrc`:

```vim
Plug 'path/to/subunit/vim'
```

### Option 3: Pathogen

If you use Pathogen:

```bash
cd ~/.vim/bundle
ln -s /path/to/subunit/vim subunit
```
