use std::io::{self, BufRead, Write};

fn main() -> io::Result<()> {
    let stdin = io::stdin();
    let mut stdout = io::BufWriter::new(io::stdout().lock());
    for line in stdin.lock().split(b'\n') {
        let line = line?;
        if line.is_empty() {
            continue;
        }
        stdout.write_all(&march_core::run_json(&line))?;
        stdout.write_all(b"\n")?;
        stdout.flush()?;
    }
    Ok(())
}
