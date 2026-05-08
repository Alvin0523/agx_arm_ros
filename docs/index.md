---
icon: lucide/rocket
---

# Documentation Index

Start here. Each page covers one topic — read only what you need.

---

## Where do I start?

```
New to this project?
  └── Read this page, then go to quick-start.md

Running the demo for the first time?
  └── quick-start.md

Need to record a new arm position?
  └── teaching.md

Setting up the Acconeer radar sensor?
  └── sensor.md

Want to understand the full operation flow?
  └── operation.md

Arm failing / planning errors / too slow?
  └── tuning.md

CAN bus issues?
  └── CAN_USER_EN.md  (English)
  └── CAN_USER.md     (中文)

Something else broken?
  └── Q&A.md
```

---

## File Reference

| File | What's in it |
|------|--------------|
| [quick-start.md](quick-start.md) | All pixi tasks, four-terminal startup order, disable arm |
| [teaching.md](teaching.md) | How to record TCP poses, copy into config, gripper control |
| [sensor.md](sensor.md) | Acconeer A121 udev rules, USB setup, how detection drives gestures |
| [operation.md](operation.md) | Step-by-step for chess loop and sensor-driven mode, config file map |
| [tuning.md](tuning.md) | Workspace box, IK tolerances, planning time, speed scaling |
| [CAN_USER_EN.md](CAN_USER_EN.md) | CAN module activation and configuration (English) |
| [CAN_USER.md](CAN_USER.md) | CAN 模块激活与配置（中文） |
| [Q&A.md](Q&A.md) | Known issues and solutions |
| [README_CN.md](README_CN.md) | Full Chinese README (original upstream) |
| [README_EN.md](README_EN.md) | Full English README (original upstream) |
| [tcp_offset/TCP_OFFSET.md](tcp_offset/TCP_OFFSET.md) | TCP offset calculation and configuration |

## Examples

### Admonitions

> Go to [documentation](https://zensical.org/docs/authoring/admonitions/)

!!! note

    This is a **note** admonition. Use it to provide helpful information.

!!! warning

    This is a **warning** admonition. Be careful!

### Details

> Go to [documentation](https://zensical.org/docs/authoring/admonitions/#collapsible-blocks)

??? info "Click to expand for more info"

    This content is hidden until you click to expand it.
    Great for FAQs or long explanations.

## Code Blocks

> Go to [documentation](https://zensical.org/docs/authoring/code-blocks/)

``` python hl_lines="2" title="Code blocks"
def greet(name):
    print(f"Hello, {name}!") # (1)!

greet("Python")
```

1.  > Go to [documentation](https://zensical.org/docs/authoring/code-blocks/#code-annotations)

    Code annotations allow to attach notes to lines of code.

Code can also be highlighted inline: `#!python print("Hello, Python!")`.

## Content tabs

> Go to [documentation](https://zensical.org/docs/authoring/content-tabs/)

=== "Python"

    ``` python
    print("Hello from Python!")
    ```

=== "Rust"

    ``` rs
    println!("Hello from Rust!");
    ```

## Diagrams

> Go to [documentation](https://zensical.org/docs/authoring/diagrams/)

``` mermaid
graph LR
  A[Start] --> B{Error?};
  B -->|Yes| C[Hmm...];
  C --> D[Debug];
  D --> B;
  B ---->|No| E[Yay!];
```

## Footnotes

> Go to [documentation](https://zensical.org/docs/authoring/footnotes/)

Here's a sentence with a footnote.[^1]

Hover it, to see a tooltip.

[^1]: This is the footnote.


## Formatting

> Go to [documentation](https://zensical.org/docs/authoring/formatting/)

- ==This was marked (highlight)==
- ^^This was inserted (underline)^^
- ~~This was deleted (strikethrough)~~
- H~2~O
- A^T^A
- ++ctrl+alt+del++

## Icons, Emojis

> Go to [documentation](https://zensical.org/docs/authoring/icons-emojis/)

* :sparkles: `:sparkles:`
* :rocket: `:rocket:`
* :tada: `:tada:`
* :memo: `:memo:`
* :eyes: `:eyes:`

## Maths

> Go to [documentation](https://zensical.org/docs/authoring/math/)

$$
\cos x=\sum_{k=0}^{\infty}\frac{(-1)^k}{(2k)!}x^{2k}
$$

!!! warning "Needs configuration"
    Note that MathJax is included via a `script` tag on this page and is not
    configured in the generated default configuration to avoid including it
    in a pages that do not need it. See the documentation for details on how
    to configure it on all your pages if they are more Maths-heavy than these
    simple starter pages.

<script id="MathJax-script" src="https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js"></script>
<script>
  window.MathJax = {
    tex: {
      inlineMath: [["\\(", "\\)"]],
      displayMath: [["\\[", "\\]"]],
      processEscapes: true,
      processEnvironments: true
    },
    options: {
      ignoreHtmlClass: ".*|",
      processHtmlClass: "arithmatex"
    }
  };

  document$.subscribe(() => {
    MathJax.startup.output.clearCache()
    MathJax.typesetClear()
    MathJax.texReset()
    MathJax.typesetPromise()
  })
</script>

## Task Lists

> Go to [documentation](https://zensical.org/docs/authoring/lists/#using-task-lists)

* [x] Install Zensical
* [x] Configure `zensical.toml`
* [x] Write amazing documentation
* [ ] Deploy anywhere

## Tooltips

> Go to [documentation](https://zensical.org/docs/authoring/tooltips/)

[Hover me][example]

  [example]: https://example.com "I'm a tooltip!"
