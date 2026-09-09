#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.10"
# dependencies = ["trio"]
# ///
"""_burn after s/reading/writing_"""

import curses
import random
import string
import sys
from collections import deque
from dataclasses import dataclass

import trio


@dataclass
class Line:
    cells: list[tuple[str, int]]
    """(character, curses attributes)"""

    y: int | None = None
    cancel_scope: trio.CancelScope | None = None


def set_cell(screen, line, x, char, color=-1, attr=0):
    if line.y is None:
        return

    attr |= curses.color_pair(color + 1)
    line.cells[x] = (char, attr)
    screen.addstr(line.y, x, char, attr)
    screen.refresh()


def draw_line(screen, line):
    if line.y is None:
        return

    for x, (char, attr) in enumerate(line.cells):
        screen.addstr(line.y, x, char, attr)


async def burn_character(screen, line, x):
    char, _ = line.cells[x]

    await trio.sleep(random.uniform(0, 1))
    set_cell(
        screen, line, x, char, random.choice((curses.COLOR_RED, curses.COLOR_YELLOW))
    )

    await trio.sleep(random.uniform(2, 5))
    set_cell(screen, line, x, random.choice(string.ascii_lowercase), attr=curses.A_DIM)


async def burn(screen, line, *, task_status=trio.TASK_STATUS_IGNORED):
    async with trio.open_nursery() as nursery:
        task_status.started(nursery.cancel_scope)
        for x in range(len(line.cells)):
            nursery.start_soon(burn_character, screen, line, x)


async def read_key(screen):
    await trio.lowlevel.checkpoint()

    while True:
        try:
            return screen.get_wch()
        except curses.error:
            await trio.lowlevel.wait_readable(sys.stdin.fileno())


def draw_input(screen, draft, height):
    screen.move(height - 1, 0)
    screen.clrtoeol()
    screen.addstr(f"> {draft}▏")
    screen.refresh()


def redraw(screen, lines, draft, height):
    screen.erase()

    for i, line in enumerate(lines):
        y = height - 1 - len(lines) + i
        line.y = y if y >= 0 else None
        draw_line(screen, line)

    draw_input(screen, draft, height)


async def app(screen):
    height, width = screen.getmaxyx()
    screen.nodelay(True)
    curses.set_escdelay(25)
    curses.curs_set(0)
    curses.use_default_colors()

    for color in range(8):
        curses.init_pair(color + 1, color, -1)

    lines: deque[Line] = deque(maxlen=height - 1)
    draft = ""
    redraw(screen, lines, draft, height)

    async with trio.open_nursery() as nursery:
        while True:
            key = await read_key(screen)

            if key in ("\n", "\r", curses.KEY_ENTER):
                if len(lines) == lines.maxlen:
                    oldest = lines.popleft()
                    oldest.y = None
                    if oldest.cancel_scope is not None:
                        oldest.cancel_scope.cancel()

                line = Line([(char, 0) for char in draft])
                lines.append(line)
                draft = ""
                redraw(screen, lines, draft, height)
                line.cancel_scope = await nursery.start(burn, screen, line)
            elif key in ("\b", "\x7f", curses.KEY_BACKSPACE):
                draft = draft[:-1]
                draw_input(screen, draft, height)
            elif (
                isinstance(key, str)
                and key.isascii()
                and key.isprintable()
                and len(draft) < width - 4
            ):
                draft += key
                draw_input(screen, draft, height)


if __name__ == "__main__":
    try:
        curses.wrapper(lambda screen: trio.run(app, screen))
    except* KeyboardInterrupt:
        pass
