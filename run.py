import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


class AsmBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ASM Builder (Linux / Bare Metal / Windows + QEMU)")

        # File selection
        tk.Label(root, text="Select .asm/.S file:").pack(pady=(10, 0))
        self.file_entry = tk.Entry(root, width=60)
        self.file_entry.pack(padx=10, pady=5)
        tk.Button(root, text="Browse", command=self.browse_file).pack()

        # Target OS
        tk.Label(root, text="Build Target:").pack(pady=(10, 0))
        self.os_target = tk.StringVar(value="Linux")
        self.os_dropdown = ttk.Combobox(root, textvariable=self.os_target, values=["Linux", "Bare Metal", "Windows"], state="readonly")
        self.os_dropdown.pack(pady=5)

        # Bit mode
        self.mode = tk.StringVar(value="64")
        tk.Label(root, text="Architecture:").pack(pady=(10, 0))
        self.mode_dropdown = ttk.Combobox(root, textvariable=self.mode, values=["32", "64", "x86"], state="readonly")
        self.mode_dropdown.pack(pady=5)

        # Assembler choice
        tk.Label(root, text="Assembler:").pack(pady=(10, 0))
        self.assembler = tk.StringVar(value="NASM")
        self.assembler_dropdown = ttk.Combobox(root, textvariable=self.assembler, values=["NASM", "GAS (GCC)"], state="readonly")
        self.assembler_dropdown.pack(pady=5)

        # Custom Command Entry
        tk.Label(root, text="Custom Command to Run After Build:").pack(pady=(10, 0))
        self.custom_command_entry = tk.Entry(root, width=60)
        self.custom_command_entry.pack(padx=10, pady=5)

        # QEMU checkbox
        self.run_qemu = tk.BooleanVar()
        tk.Checkbutton(root, text="Run in QEMU (bare metal only)", variable=self.run_qemu).pack(pady=(5, 10))

        # Build button
        tk.Button(root, text="Build", command=self.build_and_run).pack(pady=10)

        # Output box
        self.output_text = scrolledtext.ScrolledText(root, width=75, height=22)
        self.output_text.pack(padx=10, pady=(5, 10))

    def browse_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Assembly files", "*.asm *.S")])
        if filepath:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filepath)

    def build_and_run(self):
        asm_path = self.file_entry.get().strip()
        bit_mode = self.mode.get()
        os_target = self.os_target.get()
        assembler = self.assembler.get()
        custom_command = self.custom_command_entry.get().strip()

        if not asm_path or not os.path.isfile(asm_path):
            messagebox.showerror("Error", "Please select a valid assembly file.")
            return

        filename = os.path.splitext(os.path.basename(asm_path))[0]
        file_dir = os.path.dirname(asm_path)

        self.output_text.delete(1.0, tk.END)

        try:
            if os_target == "Linux":
                self.build_linux(asm_path, filename, file_dir, bit_mode, assembler)
            elif os_target == "Windows":
                self.build_windows(asm_path, filename, file_dir, bit_mode, assembler)
            else:
                self.build_bare_metal(asm_path, filename, file_dir)

            # After build is complete, execute custom command or echo status
            if custom_command:
                self.output_text.insert(tk.END, f"🔧 Running custom command: {custom_command}\n")
                result = subprocess.run(f"bash -c '{custom_command}'", shell=True, capture_output=True, text=True)
                self.output_text.insert(tk.END, result.stdout or "(no output)\n")
                if result.stderr:
                    self.output_text.insert(tk.END, "\n⚠️ STDERR:\n" + result.stderr)
            else:
                self.output_text.insert(tk.END, "🔧 Running ./test...\n")
                # Run the built file and capture the exit code separately
                test_cmd = f"./{filename}"
                result = subprocess.run(test_cmd, capture_output=True, text=True)
                self.output_text.insert(tk.END, result.stdout or "(no output)\n")
                if result.stderr:
                    self.output_text.insert(tk.END, "\n⚠️ STDERR:\n" + result.stderr)
                # Now echo the exit status
                self.output_text.insert(tk.END, f"\nExit code: {result.returncode}\n")

        except subprocess.CalledProcessError as e:
            self.output_text.insert(tk.END, f"❌ Build error:\n{e}\n")
            messagebox.showerror("Build Failed", "Check output for error details.")

    def build_linux(self, asm_path, filename, file_dir, bit_mode, assembler):
        out_file = os.path.join(file_dir, filename)

        if assembler == "GAS (GCC)":
            self.output_text.insert(tk.END, "📘 Using GAS-style (GCC) assembly.\n")
            gcc_cmd = [
                "gcc",
                "-nostdlib",
                "-static",
                "-m64" if bit_mode == "64" else "-m32" if bit_mode == "32" else "-m16",  # Adjust for x86 as 16-bit
                asm_path,
                "-o", out_file
            ]
            self.output_text.insert(tk.END, f"🔧 Compiling with GCC: {' '.join(gcc_cmd)}\n")
            subprocess.run(gcc_cmd, check=True)
        else:
            # Use NASM
            obj_file = os.path.join(file_dir, f"{filename}.o")
            nasm_format = "elf" if bit_mode == "32" else "elf64" if bit_mode == "64" else "elf"  # Adjust for x86 as 16-bit
            ld_mode = "elf_i386" if bit_mode == "32" else "elf_x86_64" if bit_mode == "64" else "elf"  # Adjust for x86

            nasm_cmd = ["nasm", "-f", nasm_format, asm_path, "-o", obj_file]
            ld_cmd = ["ld", "-m", ld_mode, "-o", out_file, obj_file]

            self.output_text.insert(tk.END, f"🔧 Assembling with NASM: {' '.join(nasm_cmd)}\n")
            subprocess.run(nasm_cmd, check=True)

            self.output_text.insert(tk.END, f"🔗 Linking with LD: {' '.join(ld_cmd)}\n")
            subprocess.run(ld_cmd, check=True)

        self.output_text.insert(tk.END, f"✅ Built Linux ELF: {out_file}\n\n▶️ Running...\n\n")
        result = subprocess.run([out_file], capture_output=True, text=True)
        self.output_text.insert(tk.END, result.stdout or "(no output)\n")
        if result.stderr:
            self.output_text.insert(tk.END, "\n⚠️ STDERR:\n" + result.stderr)

    def build_windows(self, asm_path, filename, file_dir, bit_mode, assembler):
        out_file = os.path.join(file_dir, f"{filename}.exe")

        if assembler == "GAS (GCC)":
            self.output_text.insert(tk.END, "📘 Using GAS-style (GCC) assembly.\n")
            mingw_cmd = [
                "x86_64-w64-mingw32-gcc",  # For 64-bit Windows, use the appropriate toolchain
                "-nostdlib",
                "-static",
                "-m64" if bit_mode == "64" else "-m32",  # 64-bit or 32-bit
                asm_path,
                "-o", out_file
            ]
            self.output_text.insert(tk.END, f"🔧 Compiling with MinGW: {' '.join(mingw_cmd)}\n")
            subprocess.run(mingw_cmd, check=True)
        else:
            # Use NASM for Windows
            obj_file = os.path.join(file_dir, f"{filename}.o")
            nasm_format = "win32" if bit_mode == "32" else "win64"

            nasm_cmd = ["nasm", "-f", nasm_format, asm_path, "-o", obj_file]
            ld_cmd = ["x86_64-w64-mingw32-ld", "-o", out_file, obj_file]  # Use MinGW linker

            self.output_text.insert(tk.END, f"🔧 Assembling with NASM: {' '.join(nasm_cmd)}\n")
            subprocess.run(nasm_cmd, check=True)

            self.output_text.insert(tk.END, f"🔗 Linking with MinGW LD: {' '.join(ld_cmd)}\n")
            subprocess.run(ld_cmd, check=True)

        self.output_text.insert(tk.END, f"✅ Built Windows Executable: {out_file}\n")

    def build_bare_metal(self, asm_path, filename, file_dir):
        bin_file = os.path.join(file_dir, f"{filename}.bin")

        nasm_cmd = ["nasm", "-f", "bin", asm_path, "-o", bin_file]
        self.output_text.insert(tk.END, f"💾 Assembling flat binary: {' '.join(nasm_cmd)}\n")
        subprocess.run(nasm_cmd, check=True)

        self.output_text.insert(tk.END, f"✅ Built bare metal binary: {bin_file}\n")

        if self.run_qemu.get():
            self.output_text.insert(tk.END, "🚀 Launching in QEMU...\n\n")
            qemu_cmd = ["qemu-system-i386", "-drive", f"format=raw,file={bin_file}"]
            subprocess.run(qemu_cmd)
        else:
            self.output_text.insert(tk.END, "💡 QEMU not selected. Binary is ready to boot.\n")


def main():
    root = tk.Tk()
    app = AsmBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
