import re
from pathlib import Path


def parse_entries(content: str) -> list[str]:
    lines = content.splitlines()
    entries = []
    current_entry = []
    
    for line in lines:
        if line.startswith("## ["):
            if current_entry:
                entries.append("\n".join(current_entry).strip())
            current_entry = [line]
        else:
            if current_entry:
                current_entry.append(line)
            else:
                if line.strip():
                    entries.append(line.strip())
                    
    if current_entry:
        entries.append("\n".join(current_entry).strip())
        
    return entries

def rotate_log(wiki_dir: Path, threshold_bytes: int = 30000, keep_count: int = 30) -> bool:
    log_file = wiki_dir / "log.md"
    if not log_file.exists():
        return False
        
    if log_file.stat().st_size <= threshold_bytes:
        return False
        
    content = log_file.read_text()
    entries = parse_entries(content)
    
    if len(entries) <= keep_count:
        return False
        
    entries_to_archive = entries[:-keep_count]
    entries_to_keep = entries[-keep_count:]
    
    archive_dir = wiki_dir / "log"
    archive_dir.mkdir(exist_ok=True)
    
    # Group by YYYY-MM
    date_re = re.compile(r"^## \[(\d{4}-\d{2})-\d{2}\]")
    archives = {}
    
    for entry in entries_to_archive:
        m = date_re.search(entry)
        month = m.group(1) if m else "unknown"
            
        if month not in archives:
            archives[month] = []
        archives[month].append(entry)
        
    for month, archived_entries in archives.items():
        archive_file = archive_dir / f"{month}.md"
        with open(archive_file, "a") as f:
            for e in archived_entries:
                f.write(e + "\n\n")
                
    with open(log_file, "w") as f:
        for e in entries_to_keep:
            f.write(e + "\n\n")
            
    return True
