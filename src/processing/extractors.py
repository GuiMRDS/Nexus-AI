

def _extract_markdown(path: Path) -> list[ExtractedSection]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    sections: list[ExtractedSection] = []
    heading: str | None = None
    buffer: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if buffer:
                body = clean_markdown("\n".join(buffer)).strip()
                if body:
                    sections.append(ExtractedSection(body, "section", heading or "document", heading))
                buffer = []
            heading = clean_markdown(stripped).strip() or heading
            if heading:
                sections.append(ExtractedSection(heading, "section", heading, heading))
        elif stripped:
            buffer.append(line)
        elif buffer:
            body = clean_markdown("\n".join(buffer)).strip()
            if body:
                sections.append(ExtractedSection(body, "section", heading or "document", heading))
            buffer = []
    if buffer:
        body = clean_markdown("\n".join(buffer)).strip()
        if body:
            sections.append(ExtractedSection(body, "section", heading or "document", heading))
    return sections


def _extract_csv(path: Path) -> list[ExtractedSection]:
    sections: list[ExtractedSection] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        sample = file.read(4096)
        file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(file, dialect))
    if not rows:
        return sections
    headers = rows[0]
    lines: list[str] = []
    for row_number, row in enumerate(rows[1:], start=2):
        pairs = []
        for index, value in enumerate(row):
            if not value.strip():
                continue
            header = headers[index].strip() if index < len(headers) and headers[index].strip() else f"Coluna {index + 1}"
            pairs.append(f"{header}: {value.strip()}")
        if pairs:
            lines.append(f"Linha {row_number} — " + "; ".join(pairs))
    if lines:
        sections.append(ExtractedSection("\n".join(lines), "rows", f"2-{len(rows)}"))
    elif any(value.strip() for value in headers):
        sections.append(ExtractedSection("Cabeçalhos: " + " | ".join(headers), "row", 1))
    return sections


def _extract_json(path: Path) -> list[ExtractedSection]:
    data: Any = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    text = _json_to_text(data)
    return [ExtractedSection(text, "json_path", "$" )] if text else []


def _json_to_text(value: Any, prefix: str = "") -> str:
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, (dict, list)):
                nested = _json_to_text(item, key_path)
                if nested:
                    lines.append(nested)
            else:
                lines.append(f"{key_path}: {item}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            lines.append(_json_to_text(item, f"{prefix}[{index}]"))
    else:
        lines.append(f"{prefix}: {value}" if prefix else str(value))
    return "\n".join(line for line in lines if line)


def _extract_html(path: Path) -> list[ExtractedSection]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_text(encoding="utf-8-sig", errors="replace"), "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        element.decompose()
    sections: list[ExtractedSection] = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
        text = element.get_text(" ", strip=True)
        if text:
            kind = "section" if element.name.startswith("h") else "paragraph"
            sections.append(ExtractedSection(text, kind, element.name))
    if not sections:
        text = soup.get_text("\n", strip=True)
        if text:
            sections.append(ExtractedSection(text, "document", None))
    return sections


def _extract_text(path: Path) -> list[ExtractedSection]:
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    return [ExtractedSection(text, "document", None)] if text else []