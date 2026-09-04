"""
demo/build_demo_data.py

Generates two small but realistic-looking PDF manuals used to demonstrate
every mandatory hackathon requirement:

  - Machine A / Model X200  -> demo/manuals/machine_a_x200.pdf
  - Machine B / Model H500  -> demo/manuals/machine_b_h500.pdf

Both manuals define an "E101" error code with a DIFFERENT meaning, which is
exactly the cross-manual ambiguity scenario the retriever/pipeline must
handle. Machine A's manual also contains general "overheating" language (no
explicit code) so natural-language queries can be tested, and neither
manual mentions anything about "clicking noises" so that query is
guaranteed to come back "insufficient".

Run:
    python -m rag.demo.build_demo_data
"""

from pathlib import Path
import fitz  # PyMuPDF

MANUALS_DIR = Path(__file__).resolve().parent / "manuals"


def _write_pdf(path: Path, pages: list):
    doc = fitz.open()
    for page_text in pages:
        page = doc.new_page()
        rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(rect, page_text, fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def build_machine_a():
    pages = [
        # Page 1 - cover / intro
        "Machine A - Industrial Press\nModel X200 Operator and Maintenance Manual\n\n"
        "1. Introduction\n\n"
        "This manual covers safe operation, routine maintenance, and troubleshooting "
        "procedures for the Machine A X200 industrial press.",
        # Page 2 - general overheating section (natural language coverage)
        "2. Motor Troubleshooting\n\n"
        "The X200 motor is designed to run continuously under rated load. If the "
        "motor housing becomes hot to the touch, the drive belt squeals, or the "
        "machine shuts down unexpectedly during a long run, the motor is likely "
        "overheating.\n\n"
        "Common causes of motor overheating on Machine A include blocked ventilation "
        "grilles, excessive motor load from an over-tightened drive belt, and "
        "prolonged operation without the scheduled cool-down interval.\n\n"
        "To resolve overheating: stop the machine immediately, allow the motor to "
        "cool for at least 30 minutes, clear any debris from the ventilation "
        "grilles, and check the drive belt tension against the setting in Section 6.",
        # Page 3 - Error code table (E101 = motor overheating for Machine A)
        "3. Error Code Reference\n\n"
        "E101 - Motor Overheating\n"
        "Meaning: The motor temperature sensor has detected a temperature above the "
        "safe operating threshold.\n"
        "Causes:\n"
        "- Blocked ventilation grilles\n"
        "- Excessive motor load due to an over-tightened drive belt\n"
        "- Continuous operation beyond the rated duty cycle\n"
        "Corrective Actions:\n"
        "- Stop the machine\n"
        "- Check ventilation grilles and clear any blockage\n"
        "- Inspect and adjust drive belt tension\n"
        "- Allow the motor to cool before restarting\n"
        "Warnings:\n"
        "- Allow the motor to cool before inspection; the housing may be hot enough "
        "to cause burns.\n\n"
        "E204 - Emergency Stop Engaged\n"
        "Meaning: The emergency stop circuit has been triggered.\n"
        "Causes:\n"
        "- E-stop button pressed\n"
        "- E-stop circuit wiring fault\n"
        "Corrective Actions:\n"
        "- Confirm no personnel are near the machine\n"
        "- Release the E-stop button and reset the controller\n"
        "Warnings:\n"
        "- Do not bypass the E-stop circuit under any circumstances.",
        # Page 4 - unrelated section, to give the chunker more material
        "4. Lubrication Schedule\n\n"
        "Apply high-temperature grease to the main bearing every 200 operating "
        "hours. Use only the grease specified in Appendix B. Over-lubrication can "
        "cause seal failure and should be avoided.",
    ]
    _write_pdf(MANUALS_DIR / "machine_a_x200.pdf", pages)


def build_machine_b():
    pages = [
        "Machine B - Hydraulic Press\nModel H500 Operator and Maintenance Manual\n\n"
        "1. Introduction\n\n"
        "This manual covers safe operation, routine maintenance, and troubleshooting "
        "procedures for the Machine B H500 hydraulic press.",
        "2. Hydraulic System Overview\n\n"
        "The H500 relies on a sealed hydraulic circuit to generate press force. "
        "Pressure is continuously monitored by the onboard controller. A drop in "
        "system pressure will trigger a fault condition and halt the press cycle.",
        "3. Error Code Reference\n\n"
        "E101 - Hydraulic Pressure Low\n"
        "Meaning: The hydraulic system pressure has dropped below the minimum "
        "operating threshold required for a safe press cycle.\n"
        "Causes:\n"
        "- Hydraulic fluid leak\n"
        "- Worn pump seals\n"
        "- Low hydraulic fluid reservoir level\n"
        "Corrective Actions:\n"
        "- Stop the press cycle immediately\n"
        "- Check the hydraulic fluid reservoir level and top up if low\n"
        "- Inspect hoses and fittings for visible leaks\n"
        "- Contact maintenance if the pump seals are suspected to be worn\n"
        "Warnings:\n"
        "- Relieve system pressure fully before opening any hydraulic line.\n\n"
        "E310 - Pump Overcurrent\n"
        "Meaning: The hydraulic pump motor drew current above the rated limit.\n"
        "Causes:\n"
        "- Pump obstruction\n"
        "- Failing pump motor\n"
        "Corrective Actions:\n"
        "- Stop the machine and isolate power\n"
        "- Inspect the pump for obstructions\n"
        "- Contact a qualified technician if the fault recurs\n",
        "4. Filter Replacement\n\n"
        "Replace the hydraulic return-line filter every 500 operating hours or "
        "immediately if the filter clog indicator activates.",
    ]
    _write_pdf(MANUALS_DIR / "machine_b_h500.pdf", pages)


def main():
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    build_machine_a()
    build_machine_b()
    print(f"Demo manuals written to: {MANUALS_DIR}")


if __name__ == "__main__":
    main()
