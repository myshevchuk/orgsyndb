#!/usr/bin/env fish
# OrgSynDB build entry point. Run `tools/build.fish help` for usage.

set -g repo (path dirname (path dirname (path resolve (status filename))))
set -g pipeline "$repo/tools/pipeline.py"
set -g required_tools emacs git python3 hugo weasyprint
set -g tested_hugo 0.162.1
set -g tested_weasyprint 70.0
set -g pagefind_version 1.5.2

set -gx TZ Europe/Berlin
set -gx LC_TIME C

function usage
    echo "usage: build.fish <subcommand> [options] [arguments]

Subcommands:
  export              export org/procedures/*.org to build/export/
  validate [ARGS...]  export, then validate every procedure; with ARGS,
                      run tools/validate.py ARGS... without exporting
  build               export, validate, build the site into public/ and
                      index it with Pagefind
  serve [--port N]    build, then serve public/ on http://127.0.0.1:N/
                      (default port 8000) until Ctrl-C
  pdf                 build, then render every procedure to
                      pdf/<file name>.pdf
  new [--md] [--ai-model ID] TITLE...
                      create a procedure stub with the next free ID in
                      org/procedures/, or md/procedures/ with --md
  clean [--all]       remove build/, public/, pdf/ and Hugo's caches;
                      --all also removes .emacs-batch/ and .tools/
  check-deps          report missing tools and the dnf line installing them
  help                show this text"
end

function fail
    echo "build.fish: error: $argv" >&2
    return 1
end

function usage_error
    echo "build.fish: error: $argv" >&2
    usage >&2
    return 2
end

function step
    echo "==> $argv"
end

function require_tools
    for tool in $argv
        if not command -q $tool
            fail "$tool not found; install it with: sudo dnf install $tool"
            return 1
        end
    end
end

function pipeline_py
    python3 "$pipeline" $argv
end

function source_roots
    # The validated content roots that exist, repo-relative.
    for root in build/export md/procedures
        if test -d "$repo/$root"
            echo $root
        end
    end
end

function validator_args
    if test -d "$repo/org/procedures"
        echo --org-root
        echo org/procedures
    end
    source_roots
end

function bootstrapped
    test -d "$repo/.emacs-batch/elpa/ox-hugo"
    and test -d "$repo/.emacs-batch/elpa/tomelr"
end

function run_export
    cd "$repo"; or return 1
    set -l log build/export.log
    step "export: recovering build/export/"
    pipeline_py recover-export build; or return 1
    step "export: planning org/procedures/"
    pipeline_py export-plan org/procedures build/export-plan.json
    or return 1
    mkdir -p build/.export-staging; or return 1
    if bootstrapped
        step "export: running ox-hugo"
    else
        step "export: installing ox-hugo and tomelr into .emacs-batch/ (first run, needs network)"
    end
    if not emacs -Q --batch -l "$repo/tools/export.el" build/export-plan.json build/.export-staging >"$log" 2>&1
        cat "$log" >&2
        fail "export failed; Emacs output is in $log"
        return 1
    end
    step "export: installing build/export/"
    pipeline_py install-export build
end

function run_validator
    cd "$repo"; or return 1
    step "validate: tools/validate.py "(string join ' ' -- (validator_args))
    python3 tools/validate.py (validator_args)
end

function run_build
    run_export; or return 1
    run_validator; or return 1
    step "build: hugo"
    rm -rf "$repo/public"; or return 1
    hugo --source "$repo/site" --minify; or return 1
    step "build: pagefind"
    set -l pagefind (pipeline_py ensure-pagefind --tools-dir "$repo/.tools")
    or return 1
    "$pagefind" --site "$repo/public"
end

function no_arguments --argument-names name
    set -e argv[1]
    if test (count $argv) -gt 0
        usage_error "$name takes no arguments: $argv"
        return 2
    end
end

function cmd_export
    no_arguments export $argv; or return 2
    require_tools emacs git python3; or return 1
    run_export
end

function cmd_validate
    if test (count $argv) -gt 0
        require_tools python3; or return 1
        python3 "$repo/tools/validate.py" $argv
        return $status
    end
    require_tools emacs git python3; or return 1
    run_export; or return 1
    run_validator
end

function cmd_build
    no_arguments build $argv; or return 2
    require_tools emacs git python3 hugo; or return 1
    run_build
end

function cmd_serve
    argparse --name=serve 'port=' -- $argv 2>/dev/null
    or begin
        usage_error "serve: unknown option in: $argv"
        return 2
    end
    if test (count $argv) -gt 0
        usage_error "serve takes no arguments: $argv"
        return 2
    end
    set -l port 8000
    if set -q _flag_port
        set port $_flag_port
    end
    if not string match -qr '^[0-9]{1,5}$' -- $port
        or test $port -lt 1 -o $port -gt 65535
        usage_error "--port must be a number from 1 to 65535: $port"
        return 2
    end
    require_tools emacs git python3 hugo; or return 1
    run_build; or return 1
    # Announce only once http.server has bound the port.
    PYTHONUNBUFFERED=1 python3 -m http.server --bind 127.0.0.1 \
        --directory "$repo/public" $port | while read -l line
        if string match -q 'Serving HTTP on *' -- $line
            echo "serving http://127.0.0.1:$port/ (Ctrl-C to stop)"
        else
            echo $line
        end
    end
    return $pipestatus[1]
end

function cmd_pdf
    no_arguments pdf $argv; or return 2
    require_tools emacs git python3 hugo weasyprint; or return 1
    run_build; or return 1
    step "pdf: rendering procedure pages into pdf/"
    rm -rf "$repo/pdf"; or return 1
    pipeline_py pdf --public "$repo/public" --pdf-dir "$repo/pdf" (source_roots)
end

function cmd_new
    argparse --name=new md 'ai-model=' -- $argv 2>/dev/null
    or begin
        usage_error "new: unknown option in: $argv"
        return 2
    end
    set -l title (string join ' ' -- $argv | string trim)
    if test -z "$title"
        usage_error "new needs a TITLE"
        return 2
    end
    require_tools python3; or return 1
    set -l options --repo "$repo"
    if set -q _flag_md
        set -a options --md
    end
    if set -q _flag_ai_model
        set -a options --ai-model $_flag_ai_model
    end
    cd "$repo"; or return 1
    pipeline_py new $options -- $title
end

function cmd_clean
    argparse --name=clean all -- $argv 2>/dev/null
    or begin
        usage_error "clean: unknown option in: $argv"
        return 2
    end
    if test (count $argv) -gt 0
        usage_error "clean takes no arguments: $argv"
        return 2
    end
    set -l targets build public pdf site/.hugo_build.lock site/resources
    if set -q _flag_all
        set -a targets .emacs-batch .tools
    end
    step "clean: "(string join ', ' -- $targets)
    for target in $targets
        rm -rf "$repo/$target"; or return 1
    end
end

function version_note --argument-names tested
    # Runs argv[2..] and prints " (tested with TESTED)" when the version
    # it reports is another one.
    set -l reported ($argv[2..] 2>/dev/null | string match -rg '(\d+\.\d+(?:\.\d+)?)')[1]
    if test "$reported" != "$tested"
        echo " (tested with $tested)"
    end
end

function cmd_check_deps
    no_arguments check-deps $argv; or return 2
    set -l missing
    for tool in $required_tools
        if command -q $tool
            set -l note
            switch $tool
                case hugo
                    set note (version_note $tested_hugo hugo version)
                case weasyprint
                    set note (version_note $tested_weasyprint weasyprint --version)
            end
            echo "ok      $tool$note"
        else
            echo "missing $tool"
            set -a missing $tool
        end
    end
    if command -q caddy
        echo "optional caddy (installed; only for deploy/Caddyfile.example)"
    else
        echo "optional caddy (not installed; only for deploy/Caddyfile.example)"
    end
    if test -f "$repo/.tools/pagefind-$pagefind_version/pagefind"
        echo "auto    pagefind $pagefind_version (cached in .tools/)"
    else
        echo "auto    pagefind $pagefind_version (fetched from GitHub on first build)"
    end
    if bootstrapped
        echo "auto    ox-hugo/tomelr (cached in .emacs-batch/)"
    else
        echo "auto    ox-hugo/tomelr (fetched from GitHub on first export)"
    end
    if set -q missing[1]
        echo "sudo dnf install $missing"
        return 1
    end
end

function main
    if not set -q argv[1]
        usage_error "no subcommand given"
        return 2
    end
    set -l command $argv[1]
    set -e argv[1]
    switch $command
        case help -h --help
            usage
            return 0
        case export validate build serve pdf new clean check-deps
        case '*'
            usage_error "unknown subcommand: $command"
            return 2
    end
    if not test -f "$repo/tools/build.fish" -a -f "$repo/site/hugo.toml"
        fail "$repo does not look like the OrgSynDB repository"
        return 1
    end
    switch $command
        case export
            cmd_export $argv
        case validate
            cmd_validate $argv
        case build
            cmd_build $argv
        case serve
            cmd_serve $argv
        case pdf
            cmd_pdf $argv
        case new
            cmd_new $argv
        case clean
            cmd_clean $argv
        case check-deps
            cmd_check_deps $argv
    end
end

main $argv
exit $status
