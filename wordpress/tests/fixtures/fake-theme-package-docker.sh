#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" >>"$FAKE_DOCKER_LOG"
kind="${1:-}"
action="${2:-}"
project_name=''
for argument in "$@"; do
  if [[ "$argument" == label=com.docker.compose.project=* ]]; then
    project_name="${argument##*=}"
  fi
done

if [[ "$kind" =~ ^(container|volume|network|image)$ && "$action" == ls ]]; then
  count_file="$FAKE_DOCKER_STATE/${kind}-queries"
  count=0
  [[ ! -f "$count_file" ]] || count="$(<"$count_file")"
  count=$((count + 1))
  printf '%s\n' "$count" >"$count_file"
  if [[ "$FAKE_DOCKER_MODE" == image-collision && "$kind" == image ]]; then
    printf '%s\n' 'occupied-image-id'
  elif [[ "$kind" == volume && "$count" -eq 2 ]]; then
    printf '%s\n' "${project_name}_browser-artifacts"
  fi
  exit 0
fi

if [[ "$kind" == run && " $* " == *' -C /artifacts -cf - . '* ]]; then
  if [[ "$FAKE_DOCKER_MODE" == collection-error ]]; then
    exit 75
  fi
  printf '%s' 'complete-browser-artifact-volume'
  exit 0
fi

if [[ "$kind" == compose ]]; then
  case " $* " in
    *' up --detach --wait db wordpress '*) exit 88 ;;
    *' ps --all '*) exit 0 ;;
    *' down --volumes --remove-orphans --rmi local '*) exit 0 ;;
    *) exit 99 ;;
  esac
fi

exit 99
