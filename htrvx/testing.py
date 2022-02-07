from collections import defaultdict, Counter
from typing import Iterable, List

import click
from lxml import etree

from htrvx.schemas import Validator, Schemas, simplify_log_line
from htrvx.zones import AltoXML, PageXML

Space1 = "  "
Space2 = "    "


def _empty_or_wrong(category):
    if category is None:
        return " is not categorized"
    return f" has a forbidden type (`{category}`)"


def _get_ids(ids):
    return ", ".join([f"#{val}" for val in ids])


def _print_segmonto(file_name, verbose, zone_error, line_errors, group=False):
    if zone_error or line_errors:
        click.echo(click.style(f"{Space1}× Segmonto test for {file_name}: Invalid ({len(zone_error)} wrongly tagged zones, "
                               f"{len(line_errors)} wrongly tagged lines)", fg="red"), color=True)
        if verbose:
            if group:
                zones = defaultdict(list)
                for zone in zone_error:
                    zones[f"`{zone.category}`" if zone.category is not None else "*Empty*"].append(zone.id)

                lines = defaultdict(list)
                for line in line_errors:
                    lines[f"`{line.category}`" if line.category is not None else "*Empty*"].append(line.id)

                if zones:
                    for tag_name, ids in sorted(list(zones.items()), key=lambda x: x[0]):
                        click.secho(
                            f"{Space2}→ {tag_name} tag for zones is forbidden ({len(ids)} annotations): "
                            f"{_get_ids(ids)}",
                            fg="yellow", color=True
                        )
                if lines:
                    for tag_name, ids in sorted(list(lines.items()), key=lambda x: x[0]):
                        click.secho(
                            f"{Space2}→ {tag_name} tag for lines is forbidden ({len(ids)} annotations): "
                            f"{_get_ids(ids)}",
                            fg="yellow", color=True
                        )
            else:
                for zone in zone_error:
                    click.secho(
                        f"{Space2}→ Region with id #{zone.id} {_empty_or_wrong(zone.category)}", fg="yellow", color=True
                    )
                for line in line_errors:
                    click.secho(
                        f"{Space2}→ Line with id #{line.id} {_empty_or_wrong(line.category)}", fg="yellow", color=True
                    )
    else:
        click.echo(click.style(f"{Space1}✓ Segmonto test for {file_name}: Valid", fg="green"), color=True)


def print_error_log(error_log: Iterable[etree._LogEntry], group: bool = False) -> None:
    errors = defaultdict(list)
    for line in error_log:
        if group:
            errors[simplify_log_line(line)].append(str(line.line))
        else:
            click.secho(
                f"{Space2}→ Line {line.line:04d}: {simplify_log_line(line)}",
                fg="yellow",
                color=True
            )

    for error, lines in errors.items():
        click.secho(
            f"{Space2}→ {error} on line(s): {', '.join(lines)}",
            fg="yellow",
            color=True
        )


def apply_tests(
        files: Iterable[str], verbose: bool = False, group: bool = True,
        format: str = "alto", segmonto: bool = True,
        xsd: bool = False):
    failed = False
    statuses: List[int] = []
    if format == "alto":
        cls = AltoXML
    elif format == "page":
        cls = PageXML

    for file_name in files:
        file_correct = 1
        if verbose:
            click.secho(f"⋯ Testing {file_name}")

        if segmonto:
            obj = cls(file_name)
            zone_error, line_errors = obj.test()
            _print_segmonto(file_name=file_name, verbose=verbose, zone_error=zone_error, line_errors=line_errors,
                            group=group)
            if zone_error or line_errors:
                failed = True
                file_correct = 0

        if xsd:
            failed = False
            validator = Validator(Schemas.get(format))
            if validator.validate(file_name):
                click.echo(f"{Space1}✓ Schema for {file_name}: Valid")
            else:
                failed = True
                click.echo(click.style(f"{Space1}× Schema for {file_name}: Invalid", fg="red"), color=True)
                if verbose:
                    print_error_log(validator.xmlschema.error_log, group=group)
                file_correct = 0

        statuses.append(file_correct)

    click.echo("\n\n\n=====\nREPORT\n=====\n")
    click.echo(f"{sum(statuses)}/{len(statuses)} invalid XML files")

    return failed

