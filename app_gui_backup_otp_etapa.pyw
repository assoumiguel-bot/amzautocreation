import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import re
import random
import subprocess
import os
import sys
import asyncio

COUNTRIES = [
    "United States", "United Kingdom", "Germany", "France", "Netherlands",
    "Canada", "Australia", "Japan", "Spain", "Italy", "Brazil", "India",
    "Singapore", "Sweden", "Switzerland", "Belgium", "Poland", "Turkey"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VPN_BOT_PATH = os.path.join(BASE_DIR, "VPN 0", "vpn_bot.py")
AMAZON_REGISTER_URL = "https://www.amazon.com/ap/register?openid.return_to=https%3A%2F%2Fdeveloper.amazon.com%2Fdashboard&openid.assoc_handle=mas_dev_portal&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"

async def pw_human_type(page, selector, text):
    """Playwright: ktiba b7al bashar - keyboard.press char b char"""
    try:
        el = page.locator(selector).first
        await el.evaluate("el => el.setAttribute('autocomplete', 'off')")
        await el.click()
        await page.wait_for_timeout(random.randint(100, 300))
        for char in text:
            await page.keyboard.type(char)
            await page.wait_for_timeout(random.randint(80, 200))
            if random.random() < 0.05:
                await page.wait_for_timeout(random.randint(200, 500))
        await page.keyboard.press("Escape")
    except Exception as e:
        pass

async def run_playwright_flow(app, prenom, nom, email, out_pass):
    from playwright.async_api import async_playwright
    full_name = f"{prenom} {nom}"
    app.update_status("Amazon Developer - Create Account (Playwright)...", "orange")
    app.log("1. Launching Chrome (Playwright - bla CAPTCHA)...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False, channel="chrome")
        except Exception:
            browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            app.log("2. Warmup Google...")
            await page.goto("https://www.google.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(2500, 4500))

            app.log("3. Direct amazon.com/ap/register (bla dev portal)...")
            await page.goto(AMAZON_REGISTER_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(2500, 4000))

            email_only = await page.query_selector_all("#ap_email")
            name_fields = await page.query_selector_all("#ap_customer_name")
            if email_only and not name_fields:
                app.log("   Email-first flow...")
                await pw_human_type(page, "#ap_email", email)
                await page.wait_for_timeout(1000)
                try:
                    await page.click("#continue")
                except Exception:
                    pass
                await page.wait_for_timeout(random.randint(2500, 4000))

            app.log("4. Filling form (keyboard b7al human)...")
            if await page.query_selector("#ap_customer_name"):
                await pw_human_type(page, "#ap_customer_name", full_name)
                await page.wait_for_timeout(random.randint(600, 1200))
            if await page.query_selector("#ap_email"):
                val = await page.input_value("#ap_email")
                if not val:
                    await pw_human_type(page, "#ap_email", email)
                    await page.wait_for_timeout(random.randint(600, 1200))
            if await page.query_selector("#ap_password"):
                await pw_human_type(page, "#ap_password", out_pass)
                await page.wait_for_timeout(random.randint(600, 1200))
                if await page.query_selector("#ap_password_check"):
                    await pw_human_type(page, "#ap_password_check", out_pass)
                await page.wait_for_timeout(random.randint(800, 1500))

            app.log("5. Submitting form...")
            if await page.query_selector("#continue"):
                await page.click("#continue")
            await page.wait_for_timeout(5000)

            app.log("Waiting for Amazon OTP (ou CAPTCHA)...")
            otp_selectors = ["#idTxtBx_SAOTCC_OTC", "#cvf_input_code", "#cvf-input-code", "#cvf-a-input-code", "input[name='otc']", "input[name='claimCode']", "input[type='tel']", "input[autocomplete='one-time-code']", "input[placeholder*='code']", "input[placeholder*='security']", "input[maxlength='6']"]
            otp_found = None
            otp_sel = None
            for loop in range(50):
                for sel in otp_selectors:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            otp_found = el
                            otp_sel = sel
                            break
                    except Exception:
                        pass
                if otp_found:
                    app.log("OTP input mawjoud! (Verify email) - ghadi nft7 Outlook...")
                    break
                if "cvf" in page.url:
                    app.log("CAPTCHA mawjoud (bla OTP field)! Siftiha b l'id, zed OK melli tkoun sali.")
                    app._wait_captcha_solved()
                    await page.wait_for_timeout(2000)
                    continue
                await page.wait_for_timeout(1000)

            if not otp_found:
                app.log("No OTP - logged in!")
                app.update_status("DONE - No OTP needed", "green")
                app.root.after(0, lambda: messagebox.showinfo("Najah!", "Dkhelna! Ma tlabach OTP."))
                return

            app.log("OTP requested! Tab 2 = Outlook...")
            page_outlook = await context.new_page()
            app.log("Tab 2: Outlook login...")
            await page_outlook.goto("https://login.live.com/")
            await page_outlook.wait_for_timeout(5000)

            if await page_outlook.query_selector("#i0116"):
                await pw_human_type(page_outlook, "#i0116", email)
                await page_outlook.wait_for_timeout(500)
                try:
                    await page_outlook.click("#idSIButton9")
                except Exception:
                    await page_outlook.keyboard.press("Enter")
                await page_outlook.wait_for_timeout(5000)
            if await page_outlook.query_selector("#i0118"):
                await pw_human_type(page_outlook, "#i0118", out_pass)
                await page_outlook.wait_for_timeout(500)
                try:
                    await page_outlook.click("#idSIButton9")
                except Exception:
                    await page_outlook.keyboard.press("Enter")
                await page_outlook.wait_for_timeout(4000)
                try:
                    await page_outlook.click("#idBtn_Back")
                except Exception:
                    pass
                await page_outlook.wait_for_timeout(2000)

            await page_outlook.goto("https://outlook.live.com/mail/0/")
            await page_outlook.wait_for_timeout(12000)

            app.log("Searching Amazon OTP...")
            for sel in ["#topSearchInput", "input[aria-label*='Search']", "input[placeholder*='Search']"]:
                try:
                    s = page_outlook.locator(sel).first
                    if await s.is_visible():
                        await s.click()
                        await page_outlook.wait_for_timeout(500)
                        await pw_human_type(page_outlook, sel, "Amazon")
                        await page_outlook.keyboard.press("Enter")
                        break
                except Exception:
                    continue
            await page_outlook.wait_for_timeout(8000)

            try:
                rows = await page_outlook.query_selector_all("[aria-label*='Amazon'], div[role='option']")
                for i, row in enumerate(rows[:5]):
                    txt = await row.text_content()
                    if txt and "amazon" in txt.lower():
                        await row.click()
                        await page_outlook.wait_for_timeout(4000)
                        break
            except Exception:
                pass

            await page_outlook.wait_for_timeout(3000)
            body = await page_outlook.content()
            otp_matches = re.findall(r"\b\d{6}\b", body)
            if not otp_matches:
                otp_matches = re.findall(r"\b\d{4,8}\b", body)
            if not otp_matches:
                raise Exception("Mal9inach OTP f Outlook.")
            otp = otp_matches[0]
            app.log(f"OTP = {otp}")
            with open(os.path.join(BASE_DIR, "otp.txt"), "w") as f:
                f.write(otp)

            app.log("Retour Amazon - pasting OTP...")
            await page.bring_to_front()
            await page.wait_for_timeout(2000)

            if otp_found and otp_sel:
                await otp_found.fill("")
                await pw_human_type(page, otp_sel, otp)
                await page.wait_for_timeout(500)
                try:
                    await page.click("#idSubmit_SAOTCC_Continue")
                except Exception:
                    try:
                        await page.click("#idSIButton9")
                    except Exception:
                        try:
                            await page.click("#auth-verify-button")
                        except Exception:
                            try:
                                await page.click("#cvf-input-code-btn")
                            except Exception:
                                await page.keyboard.press("Enter")
                app.log("OTP pasted!")
                app.update_status(f"DONE! OTP {otp}", "green")
                app.root.after(0, lambda o=otp: messagebox.showinfo("Najah!", f"Kamal!\nVPN → Amazon Developer → Outlook OTP\n\nOTP: {o}\nTsajel f otp.txt"))
            else:
                app.update_status(f"OTP: {otp} (paste manually)", "green")
                app.root.after(0, lambda o=otp: messagebox.showinfo("OTP", f"L'OTP: {o}\nTsajel f otp.txt\nSiftu b l'id"))

        except Exception as e:
            raise e
        finally:
            await page.wait_for_timeout(2000)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("VPN + Amazon Developer + Outlook OTP - 3 Bots")
        self.root.geometry("500x620")
        self.root.configure(padx=20, pady=15, bg="#f0f4f8")

        # Lwan: hmar #c0392b, khdar #27ae60, zra9 #3498db, sfar #f1c40f
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 9), background="#f0f4f8")
        style.configure("TLabelframe", background="#f0f4f8")
        style.configure("TLabelframe.Label", font=("Arial", 10, "bold"), foreground="#c0392b", background="#f0f4f8")

        ttk.Label(root, text="3 Bots: VPN → Amazon Developer → Outlook OTP", font=("Arial", 12, "bold"), foreground="#c0392b").pack(pady=5)

        # === 1. VPN (zra9) ===
        f_vpn = ttk.LabelFrame(root, text=" 1. VPN Surfshark (lawal) ", padding=8)
        f_vpn.pack(fill="x", pady=5)
        ttk.Label(f_vpn, text="Mode VPN:", foreground="#2980b9").grid(row=0, column=0, sticky="w", pady=2)
        self.vpn_mode = ttk.Combobox(f_vpn, width=32, state="readonly")
        self.vpn_mode['values'] = ("Connect b l'id (Manual - 7ssan)", "Bot VPN 0 (auto)")
        self.vpn_mode.current(0)
        self.vpn_mode.grid(row=0, column=1, pady=2, padx=5)
        ttk.Label(f_vpn, text="Dawla (Country):", foreground="#2980b9").grid(row=1, column=0, sticky="w", pady=2)
        self.vpn_country = ttk.Combobox(f_vpn, width=35, values=COUNTRIES)
        self.vpn_country.set("United States")
        self.vpn_country.grid(row=1, column=1, pady=2, padx=5)

        # === 2. Amazon Developer - Create Account ===
        f_acc = ttk.LabelFrame(root, text=" 2. Amazon Developer - Create Account (3amar info) ", padding=8)
        f_acc.pack(fill="x", pady=5)
        ttk.Label(f_acc, text="Prenom:", foreground="#27ae60").grid(row=0, column=0, sticky="w", pady=2)
        self.prenom = ttk.Entry(f_acc, width=40)
        self.prenom.grid(row=0, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="Nom:", foreground="#27ae60").grid(row=1, column=0, sticky="w", pady=2)
        self.nom = ttk.Entry(f_acc, width=40)
        self.nom.grid(row=1, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="Email (Amazon = Outlook):", foreground="#27ae60").grid(row=2, column=0, sticky="w", pady=2)
        self.email = ttk.Entry(f_acc, width=40)
        self.email.grid(row=2, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="Password:", foreground="#27ae60").grid(row=3, column=0, sticky="w", pady=2)
        self.outlook_pass = ttk.Entry(f_acc, width=40, show="*")
        self.outlook_pass.grid(row=3, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="(OTP ywsel f Outlook - nakhdoha f nouvel onglet)", font=("Arial", 8), foreground="#666").grid(row=4, column=1, sticky="w")
        f_btns = tk.Frame(f_acc, bg="#f0f4f8")
        f_btns.grid(row=5, column=0, columnspan=2, pady=4)
        self.load_btn = tk.Button(f_btns, text="Load", command=self.load_profile, width=8, bg="#3498db", fg="white", cursor="hand2")
        self.load_btn.pack(side="left", padx=2)
        self.save_btn = tk.Button(f_btns, text="Save", command=self.save_profile, width=8, bg="#27ae60", fg="white", cursor="hand2")
        self.save_btn.pack(side="left", padx=2)

        self.start_btn = tk.Button(root, text="▶ START - VPN → Create Amazon → OTP f Outlook", command=self.start_all,
                                   font=("Arial", 10, "bold"), bg="#27ae60", fg="white", activebackground="#2ecc71",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=15, pady=8)
        self.start_btn.pack(pady=12)

        ttk.Label(root, text="Activity Log:", foreground="#f1c40f").pack(anchor="w")
        self.log_text = tk.Text(root, height=10, width=58, font=("Consolas", 8), state="disabled", bg="#fffde7", fg="#2c3e50", insertbackground="#c0392b")
        self.log_text.pack(pady=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Wajed...")
        self.status_label = ttk.Label(root, textvariable=self.status_var, foreground="#3498db", font=("Arial", 9, "italic"))
        self.status_label.pack()

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"[*] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
        self.root.update()

    def update_status(self, text, color="blue"):
        self.status_var.set(text)
        self.status_label.configure(foreground=color)
        self.root.update()

    def load_profile(self):
        path = filedialog.askopenfilename(
            title="Load profile (EMAILNAME.txt)",
            initialdir=BASE_DIR,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            data = {"prenom": "", "nom": "", "email": "", "password": ""}
            for line in lines:
                up = line.upper()
                if up.startswith("PRENOM:"):
                    data["prenom"] = line.split(":", 1)[1].strip()
                elif up.startswith("NOM:"):
                    data["nom"] = line.split(":", 1)[1].strip()
                elif "@" in line and "." in line and " " not in line and not data["email"]:
                    data["email"] = line
                elif (not data["password"] and len(line) >= 8
                      and not up.startswith("TARGET") and not up.startswith("NOM")
                      and not up.startswith("PRENOM") and line != data["email"]):
                    data["password"] = line
            self.prenom.delete(0, tk.END)
            self.prenom.insert(0, data["prenom"])
            self.nom.delete(0, tk.END)
            self.nom.insert(0, data["nom"])
            self.email.delete(0, tk.END)
            self.email.insert(0, data["email"])
            self.outlook_pass.delete(0, tk.END)
            self.outlook_pass.insert(0, data["password"])
            self.log(f"Loaded: {path}")
        except Exception as e:
            messagebox.showerror("Load", str(e))

    def connect_vpn_surfshark(self):
        country = self.vpn_country.get().strip()
        if not country:
            country = "United States"
        mode = self.vpn_mode.get()

        if "Manual" in mode or "7ssan" in mode:
            self.log(f"Connect Surfshark to {country} b l'id daba...")
            messagebox.showinfo("VPN Manual",
                f"1. Ft7 Surfshark\n2. Connect 3la {country}\n3. Khass VPN ykon VRAIMENT connecti (timer yt7ark, ma 00:00)\n4. Zed OK melli tkoun connecti b 7al")
            self.log("User connected VPN manually. Waiting 15 sec bach ystabilize...")
            time.sleep(15)
            return True

        if not os.path.exists(VPN_BOT_PATH):
            self.log("VPN 0/vpn_bot.py mal9ach. Khad 'Connect b l'id'.")
            messagebox.showinfo("VPN", "Bot mal9ach. Khad 'Connect b l'id (Manual)' w connect b l'id.")
            return True
        self.log(f"Running Surfshark VPN bot - {country}...")
        self.log("(Surfshark mefto7 - 3 sec...)")
        time.sleep(3)
        try:
            vpn_dir = os.path.join(BASE_DIR, "VPN 0")
            dawla_file = os.path.join(vpn_dir, "dawla.txt")
            with open(dawla_file, "w", encoding="utf-8") as f:
                f.write(country)
            result = subprocess.run(
                [sys.executable, VPN_BOT_PATH],
                cwd=vpn_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                self.log("Surfshark bot salat. Waiting 20 sec bach VPN ystabilize...")
            else:
                self.log("Surfshark bot malhdemch - Jrab 'Connect b l'id'.")
        except Exception as e:
            self.log(f"VPN: {e}. Khad 'Connect b l'id'.")
        self.log("Waiting 15 sec before Chrome...")
        time.sleep(15)
        return True

    def save_profile(self):
        path = filedialog.asksaveasfilename(
            title="Save profile",
            initialdir=BASE_DIR,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            prenom = self.prenom.get().strip()
            nom = self.nom.get().strip()
            email = self.email.get().strip()
            password = self.outlook_pass.get().strip()
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"PRENOM: {prenom}\n")
                f.write(f"NOM: {nom}\n")
                f.write(f"{email}\n")
                f.write(f"{password}\n")
            self.log(f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save", str(e))

    def start_all(self):
        prenom = self.prenom.get().strip()
        nom = self.nom.get().strip()
        email = self.email.get().strip()
        out_pass = self.outlook_pass.get().strip()
        if not prenom or not nom:
            messagebox.showerror("Erreur", "Dakhel Prenom w Nom.")
            return
        if not email or not out_pass:
            messagebox.showerror("Erreur", "Dakhel email w password.")
            return
        self.start_btn.configure(state="disabled")
        self.update_status("Starting...", "orange")
        thread = threading.Thread(target=self.run_full_flow, args=(prenom, nom, email, out_pass))
        thread.daemon = True
        thread.start()

    def _wait_captcha_solved(self):
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        captcha_done = threading.Event()
        def _show():
            messagebox.showinfo("CAPTCHA - Solve b l'id", "Solve the puzzle b l'id.\nMelli tsaliw w tzad Confirm, zed OK.\nGhadi nkamlou l Outlook.")
            captcha_done.set()
        self.root.after(0, _show)
        captcha_done.wait(timeout=180)
        self.root.attributes('-topmost', False)

    def run_full_flow(self, prenom, nom, email, out_pass):
        try:
            self.connect_vpn_surfshark()
            asyncio.run(run_playwright_flow(self, prenom, nom, email, out_pass))
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            self.update_status("Erreur!", "red")
            messagebox.showerror("Error", str(e))
        finally:
            self.log("Finished.")
            self.start_btn.configure(state="normal")
            self.log("Chrome ma yt7atta7ch - Siftu b l'id (croix) melli t7ab.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
