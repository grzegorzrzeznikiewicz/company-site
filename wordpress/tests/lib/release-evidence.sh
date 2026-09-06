#!/usr/bin/env bash

GAMA_RELEASE_EVIDENCE_IMAGE='wordpress:7.1.0-php8.4-apache@sha256:b8f37de278183840a09f5a4b5bf5ec9f09177a9984d2fe5cc072b4388128bd9d'

gama_release_evidence_acquire_volume() {
  local volume="$1"
  local contract_label="$2"
  local create_status

  if docker volume inspect "$volume" >/dev/null 2>&1; then
    echo "Refusing preexisting generated evidence volume: $volume" >&2
    return 1
  fi

  docker volume create --label "$contract_label" "$volume" >/dev/null
  create_status=$?
  if [[ "$create_status" -ne 0 ]]; then
    echo "Evidence volume creation failed with status $create_status: $volume" >&2
    return "$create_status"
  fi
}

gama_release_evidence_finalize() {
  local primary_status="$1"
  local volume_acquired="$2"
  local volume="$3"
  local archive="$4"
  local final_status="$primary_status"
  local export_container="$volume-export"
  local operation_status
  local temporary_archive=''

  if [[ "$volume_acquired" -ne 1 ]]; then
    if [[ "$primary_status" -eq 0 ]]; then
      echo "Required evidence volume was not acquired: $volume" >&2
      final_status=1
    fi
    return "$final_status"
  fi

  if ! docker volume inspect "$volume" >/dev/null 2>&1; then
    echo "Required evidence volume is missing: $volume" >&2
    if [[ "$primary_status" -eq 0 ]]; then
      final_status=1
    fi
    return "$final_status"
  fi

  temporary_archive="$(mktemp "$archive.partial.XXXXXX")"
  operation_status=$?
  if [[ "$operation_status" -ne 0 ]]; then
    echo "Evidence temporary archive creation failed with status $operation_status: $archive" >&2
    if [[ "$primary_status" -eq 0 ]]; then
      final_status=1
    fi
  else
    docker run --rm --name "$export_container" --network none --volume "$volume:/artifacts:ro" --entrypoint tar \
      "$GAMA_RELEASE_EVIDENCE_IMAGE" -C /artifacts -cf - . >"$temporary_archive"
    operation_status=$?
    if [[ "$operation_status" -ne 0 ]]; then
      echo "Evidence export failed with status $operation_status: $volume" >&2
      if [[ "$primary_status" -eq 0 ]]; then
        final_status=1
      fi
    elif [[ ! -s "$temporary_archive" ]] || ! tar -tf "$temporary_archive" >/dev/null 2>&1; then
      echo "Evidence export did not produce a readable archive: $volume" >&2
      if [[ "$primary_status" -eq 0 ]]; then
        final_status=1
      fi
    else
      if ( set -o noclobber; : >"$archive" ) 2>/dev/null; then
        mv "$temporary_archive" "$archive"
        operation_status=$?
        if [[ "$operation_status" -eq 0 ]]; then
          temporary_archive=''
        else
          unlink "$archive" 2>/dev/null
        fi
      else
        operation_status=$?
      fi
      if [[ "$operation_status" -ne 0 ]]; then
        echo "Evidence archive promotion failed with status $operation_status: $archive" >&2
        if [[ "$primary_status" -eq 0 ]]; then
          final_status=1
        fi
      fi
    fi

    if [[ -n "$temporary_archive" ]]; then
      unlink "$temporary_archive"
      operation_status=$?
      if [[ "$operation_status" -ne 0 ]]; then
        echo "Owned temporary evidence cleanup failed with status $operation_status: $temporary_archive" >&2
        if [[ "$primary_status" -eq 0 ]]; then
          final_status=1
        fi
      fi
    fi
  fi

  docker volume rm "$volume" >/dev/null 2>&1
  operation_status=$?
  if [[ "$operation_status" -ne 0 ]]; then
    echo "Owned evidence volume cleanup failed with status $operation_status: $volume" >&2
    if [[ "$primary_status" -eq 0 ]]; then
      final_status=1
    fi
  elif docker volume inspect "$volume" >/dev/null 2>&1; then
    echo "Owned evidence volume remains after cleanup: $volume" >&2
    if [[ "$primary_status" -eq 0 ]]; then
      final_status=1
    fi
  fi

  return "$final_status"
}
