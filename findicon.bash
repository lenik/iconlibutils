# bash completion for findicon (iconlib search shortcut)

_findicon()
{
	local cur prev words cword
	_init_completion || return

	# Reuse iconlib search completion context
	words=(iconlib search "${words[@]:1}")
	cword=$((cword + 1))
	_iconlib
}

complete -F _findicon findicon
