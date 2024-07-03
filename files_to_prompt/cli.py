import os
from fnmatch import fnmatch
import tiktoken
import click
import jsmin
import json

def should_ignore(path, gitignore_rules):
    for rule in gitignore_rules:
        if fnmatch(os.path.basename(path), rule):
            return True
        if os.path.isdir(path) and fnmatch(os.path.basename(path) + "/", rule):
            return True
    return False

def read_gitignore(path):
    gitignore_path = os.path.join(path, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def read_ftpignore():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ftpignore_path = os.path.join(script_dir, ".ftpignore")
    if os.path.isfile(ftpignore_path):
        with open(ftpignore_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def minify_content(file_path, content):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.ts', '.tsx', '.mjs', '.js']:
        return jsmin.jsmin(content)
    elif ext == '.json':
        try:
            return json.dumps(json.loads(content), separators=(',', ':'))
        except json.JSONDecodeError:
            return content  # Return original content if JSON is invalid
    return content  # Return original content for other file types


def print_path(path, content, xml, output_file):
    minified_content = minify_content(path, content)
    if xml:
        print_as_xml(path, minified_content, output_file)
    else:
        print_default(path, minified_content, output_file)

def print_default(path, content, output_file):
    def write_output(text):
        if output_file:
            output_file.write(text + "\n")
        else:
            click.echo(text)

    write_output(path)
    write_output("---")
    write_output(content)
    write_output("")
    write_output("---")

def print_as_xml(path, content, output_file):
    def write_output(text):
        if output_file:
            output_file.write(text + "\n")
        else:
            click.echo(text)

    write_output(f'<document path="{path}">')
    write_output(content)
    write_output("</document>")

def process_path(path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns, xml, output_file):
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                content = f.read()
                print_path(path, content, xml, output_file)
        except UnicodeDecodeError:
            warning_message = f"Warning: Skipping file {path} due to UnicodeDecodeError"
            click.echo(click.style(warning_message, fg="red"), err=True)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                files = [f for f in files if not f.startswith(".")]

            if not ignore_gitignore:
                gitignore_rules.extend(read_gitignore(root))
                dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), gitignore_rules)]
                files = [f for f in files if not should_ignore(os.path.join(root, f), gitignore_rules)]

            dirs[:] = [d for d in dirs if not any(fnmatch(d, pattern) for pattern in ignore_patterns)]
            files = [f for f in files if not any(fnmatch(f, pattern) for pattern in ignore_patterns)]

            for file in sorted(files):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                        print_path(file_path, content, xml, output_file)
                except UnicodeDecodeError:
                    warning_message = f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                    click.echo(click.style(warning_message, fg="red"), err=True)

def count_tokens(file_name):
    enc = tiktoken.get_encoding("cl100k_base")
    try:
        with open(file_name, 'r') as file:
            content = file.read()
        tokens = enc.decode(enc.encode(content))
        return len(tokens)
    except FileNotFoundError:
        click.echo(click.style(f"Error: File not found - {file_name}", fg="red"), err=True)
    except Exception as e:
        click.echo(click.style(f"Error processing file {file_name}: {str(e)}", fg="red"), err=True)

@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--include-hidden", is_flag=True, help="Include files and folders starting with .")
@click.option("--ignore-gitignore", is_flag=True, help="Ignore .gitignore files and include all files")
@click.option("ignore_patterns", "--ignore", multiple=True, default=[], help="List of patterns to ignore")
@click.option("--output", type=click.Path(), help="Output file to write the results to")
@click.option("--force", is_flag=True, help="Overwrite the output file if it already exists")
@click.option("--count-tokens", "count_tokens_path", type=click.Path(exists=True), help="Count the number of tokens in the specified file")
@click.option("--xml", is_flag=True, help="Output in XML format suitable for Claude's long context window.")
@click.version_option()
def cli(paths, include_hidden, ignore_gitignore, ignore_patterns, output, count_tokens_path, xml, force):
    """
    Takes one or more paths to files or directories and outputs every file,
    recursively, each one preceded with its filename.

    If the `--xml` flag is provided, the output will be structured in XML format
    suitable for Claude's long context window.
    """
    if count_tokens_path:
        token_count = count_tokens(count_tokens_path)
        click.echo(f"Token count for {count_tokens_path}: {token_count}")
        return

    ftpignore_rules = read_ftpignore()  # Always include these rules
    output_file = None
    if output:
        if os.path.exists(output) and not force:
            click.echo(f"Error: The file '{output}' already exists. Use --force to overwrite.", err=True)
            return
        try:
            output_file = open(output, 'w')
        except IOError as e:
            click.echo(f"Error: Unable to open output file '{output}'. {str(e)}", err=True)
            return
    try:
        if xml:
            if output_file:
                output_file.write("Here are some documents for you to reference for your task:\n\n<documents>\n")
            else:
                click.echo("Here are some documents for you to reference for your task:")
                click.echo()
                click.echo("<documents>")

        for path in paths:
            ignore_rules = list(ftpignore_rules)  # Start with the global .ftpignore rules
            if not os.path.exists(path):
                raise click.BadArgumentUsage(f"Path does not exist: {path}")
            if not ignore_gitignore:
                ignore_rules.extend(read_gitignore(os.path.dirname(path)))  # Add .gitignore rules from the path's directory
            process_path(path, include_hidden, ignore_gitignore, ignore_rules, ignore_patterns, xml, output_file)

        if xml:
            if output_file:
                output_file.write("</documents>\n")
            else:
                click.echo("</documents>")
    finally:
        if output_file:
            output_file.close()

if __name__ == "__main__":
    cli()