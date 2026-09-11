# bash completion for iconlib

_iconlib()
{
	local cur prev words cword
	_init_completion || return

	local cmds='search which info libraries ls pull push browse index'
	local globals='-l -d --local-dir -s --schema -m --map -v --verbose -q --quiet -h --help --version'

	# Find subcommand
	local cmd='' i
	for ((i = 1; i < cword; i++)); do
		case ${words[i]} in
			search|which|info|libraries|ls|pull|push|browse|index)
				cmd=${words[i]}
				break
				;;
		esac
	done

	if [[ -z $cmd ]]; then
		if [[ $cur == -* ]]; then
			COMPREPLY=($(compgen -W '$globals' -- "$cur"))
		else
			COMPREPLY=($(compgen -W '$cmds' -- "$cur"))
		fi
		return
	fi

	case $cmd in
		search)
			if [[ $cur == -* ]]; then
				COMPREPLY=($(compgen -W '--long --names -l -1 -h --help' -- "$cur"))
			fi
			;;
		which)
			if [[ $cur == -* ]]; then
				COMPREPLY=($(compgen -W '-a -h --help' -- "$cur"))
			fi
			;;
		info)
			if [[ $cur == -* ]]; then
				COMPREPLY=($(compgen -W '-h --help' -- "$cur"))
			fi
			;;
		pull)
			if [[ $cur == -* ]]; then
				COMPREPLY=($(compgen -W '-F --format -S --size -h --help' -- "$cur"))
			fi
			;;
		libraries|ls)
			if [[ $cur == -* ]]; then
				COMPREPLY=($(compgen -W '-l --long -1 --names -h --help' -- "$cur"))
			fi
			;;
		push|browse)
			if [[ $cur == -* ]]; then
				COMPREPLY=($(compgen -W '-h --help' -- "$cur"))
			fi
			;;
		index)
			if [[ $cur == -* ]]; then
				COMPREPLY=($(compgen -W '-w --web -F --faiss -f --force -s --upscale -o --outdir --name --title --license --homepage --icons-root --icons-url-prefix --template --max-icons -l -h --help' -- "$cur"))
			fi
			;;
	esac
}

complete -F _iconlib iconlib
