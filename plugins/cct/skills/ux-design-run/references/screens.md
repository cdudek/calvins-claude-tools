# Screens

## Purpose

Specify every screen in words precise enough to build.
This includes layout, lists, controls, filters, copy, and component choices.

## Inputs

- `<spec>/brief.md`.
- `<spec>/ia.md`.
- `<spec>/interaction.md`.
- `docs/ux/setup.md`.
- Screen goals from setup.
- Component catalogue from setup.
- the shared `writing.md`.

## Steps

1. List each screen from IA and interaction.
2. Tie each screen to a screen goal.
3. Write the header.
   Include title, tabs, and actions.
4. Order the sections.
5. Define layout at 100 percent and 150 percent.
   Include columns and widths.
6. Specify every list.
   Include columns, sort, and empty state.
7. Write the controls table.
8. Specify filters and their defaults.
9. Write every word on screen.
10. Name the component for each region.
    Use have, new variant, or missing.

## Output Template

Write `<spec>/screens.md`.

```markdown
# Screens

## <Screen Name>

### Purpose

<from screen goals>

### Header

| Title | Tabs | Actions |
|---|---|---|

### Sections

| Order | Section | Purpose |
|---|---|---|

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | | | |
| 150 % | | | |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|

### Words

| Where | Text |
|---|---|

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
```

## Checks

- Every screen has a purpose from screen goals.
- Every action from `<spec>/interaction.md` appears as a control or menu item.
- Every control has a key.
- Every disabled state has a reason and state source.
- Every word appears in the words table.
- Every component is have, new variant, or missing.
- 150 percent layout clips nothing and hides no persistent control.

## Skip Rule

Skip when the `screens` skip is set (the shared `spec-folder.md`, section 2).
The reason is already recorded; write no file.
For S size, this file carries the screenshot of the delta.

## Optional Skills

Used only when installed; the activity runs fully without them.

- `cct:design-system-write`.
- `cct:ux-copy-write`.

Sources: github.com/openai/plugins · github.com/ratacat/claude-skills
