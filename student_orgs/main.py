from __future__ import annotations
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# ── bootstrap
load_dotenv()
sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
project_id = os.getenv("FIREBASE_PROJECT_ID")

if not sa_path or not os.path.exists(sa_path):
    print("ERROR: Set GOOGLE_APPLICATION_CREDENTIALS in .env to your service account JSON path.")
    sys.exit(1)

if not project_id:
    print("ERROR: Set FIREBASE_PROJECT_ID in .env to your Firebase project id.")
    sys.exit(1)

cred = credentials.Certificate(sa_path)
firebase_admin.initialize_app(cred, {"projectId": project_id})
db = firestore.client()

# ── data classes
@dataclass
class University:
    name: str
    domain: Optional[str] = None
    createdAt: datetime = datetime.utcnow()

@dataclass
class Club:
    name: str
    universityId: str
    description: Optional[str] = None
    createdAt: datetime = datetime.utcnow()

@dataclass
class Person:
    name: str
    email: Optional[str] = None
    studentId: Optional[str] = None
    createdAt: datetime = datetime.utcnow()

@dataclass
class Membership:
    personId: str
    role: str = "member"         # "owner"|"officer"|"member"
    status: str = "active"       # "active"|"inactive"
    title: Optional[str] = None
    createdAt: datetime = datetime.utcnow()

# ── helpers
def _print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def _choose(items: List[firestore.DocumentSnapshot], label: str) -> Optional[firestore.DocumentSnapshot]:
    if not items:
        print(f"No {label} found.")
        return None
    for idx, d in enumerate(items, start=1):
        print(f"{idx}) {d.id} :: {d.to_dict()}")
    sel = input(f"Select {label} by number (blank to cancel): ").strip()
    if not sel:
        return None
    try:
        i = int(sel) - 1
        return items[i]
    except Exception:
        print("Invalid selection.")
        return None

# ── CRUD: Universities
def create_university():
    _print_header("Create University")
    name = input("University name: ").strip()
    domain = input("Domain (optional, e.g., uta.edu): ").strip() or None
    ref = db.collection("universities").document()
    ref.set(asdict(University(name=name, domain=domain)))
    print(f"Created university: {ref.id}")

def list_universities() -> List[firestore.DocumentSnapshot]:
    snaps = list(db.collection("universities").order_by("name").stream())
    for d in snaps:
        print(f"{d.id} :: {d.to_dict()}")
    return snaps

def update_university():
    _print_header("Update University")
    snaps = list(db.collection("universities").order_by("name").stream())
    chosen = _choose(snaps, "university")
    if not chosen: return
    data = chosen.to_dict()
    new_name = input(f"New name (blank keep '{data.get('name')}'): ").strip() or data.get("name")
    new_domain = input(f"New domain (blank keep '{data.get('domain')}'): ").strip() or data.get("domain")
    chosen.reference.update({"name": new_name, "domain": new_domain})
    print("Updated.")

def delete_university():
    _print_header("Delete University")
    snaps = list(db.collection("universities").order_by("name").stream())
    chosen = _choose(snaps, "university")
    if not chosen: return

    # Danger: if you’ve created clubs under this university, you probably want to stop deletion or cascade.
    confirm = input("Type DELETE to confirm (this does NOT delete clubs): ").strip()
    if confirm == "DELETE":
        chosen.reference.delete()
        print("Deleted.")
    else:
        print("Cancelled.")

# ── CRUD: Clubs
def create_club():
    _print_header("Create Club")
    # pick university
    u_snaps = list(db.collection("universities").order_by("name").stream())
    u = _choose(u_snaps, "university")
    if not u: return

    name = input("Club name: ").strip()
    description = input("Description (optional): ").strip() or None

    ref = db.collection("clubs").document()
    ref.set(asdict(Club(name=name, universityId=u.id, description=description)))
    print(f"Created club: {ref.id}")

def list_clubs():
    _print_header("List Clubs")
    snaps = list(db.collection("clubs").order_by("name").stream())
    for d in snaps:
        print(f"{d.id} :: {d.to_dict()}")
    return snaps

def update_club():
    _print_header("Update Club")
    snaps = list(db.collection("clubs").order_by("name").stream())
    chosen = _choose(snaps, "club")
    if not chosen: return
    data = chosen.to_dict()
    new_name = input(f"New name (blank keep '{data.get('name')}'): ").strip() or data.get("name")
    new_desc = input(f"New description (blank keep '{data.get('description')}'): ").strip() or data.get("description")
    chosen.reference.update({"name": new_name, "description": new_desc})
    print("Updated.")

def delete_club():
    _print_header("Delete Club")
    snaps = list(db.collection("clubs").order_by("name").stream())
    chosen = _choose(snaps, "club")
    if not chosen: return

    # Also consider cascading delete memberships
    confirm = input("Type DELETE to confirm (this WILL delete memberships under this club): ").strip()
    if confirm == "DELETE":
        # delete memberships subcollection
        mem_snaps = list(chosen.reference.collection("memberships").stream())
        batch = db.batch()
        for m in mem_snaps:
            batch.delete(m.reference)
        batch.delete(chosen.reference)
        batch.commit()
        print("Club and its memberships deleted.")
    else:
        print("Cancelled.")

# ── CRUD: People
def create_person():
    _print_header("Create Person")
    name = input("Name: ").strip()
    email = input("Email (optional): ").strip() or None
    sid = input("Student ID (optional): ").strip() or None
    ref = db.collection("people").document()
    ref.set(asdict(Person(name=name, email=email, studentId=sid)))
    print(f"Created person: {ref.id}")

def list_people():
    _print_header("List People")
    snaps = list(db.collection("people").order_by("name").stream())
    for d in snaps:
        print(f"{d.id} :: {d.to_dict()}")
    return snaps

def update_person():
    _print_header("Update Person")
    snaps = list(db.collection("people").order_by("name").stream())
    chosen = _choose(snaps, "person")
    if not chosen: return
    data = chosen.to_dict()
    new_name = input(f"New name (blank keep '{data.get('name')}'): ").strip() or data.get("name")
    new_email = input(f"New email (blank keep '{data.get('email')}'): ").strip() or data.get("email")
    new_sid = input(f"New studentId (blank keep '{data.get('studentId')}'): ").strip() or data.get("studentId")
    chosen.reference.update({"name": new_name, "email": new_email, "studentId": new_sid})
    print("Updated.")

def delete_person():
    _print_header("Delete Person")
    snaps = list(db.collection("people").order_by("name").stream())
    chosen = _choose(snaps, "person")
    if not chosen: return
    # Note: memberships reference personId; we do not cascade delete memberships here.
    confirm = input("Type DELETE to confirm (memberships that reference this person will be stale): ").strip()
    if confirm == "DELETE":
        chosen.reference.delete()
        print("Deleted.")
    else:
        print("Cancelled.")

# ── CRUD: Memberships (under a chosen club)
def add_membership():
    _print_header("Add Membership to Club")
    club = _choose(list(db.collection("clubs").order_by("name").stream()), "club")
    if not club: return
    person = _choose(list(db.collection("people").order_by("name").stream()), "person")
    if not person: return

    role = input("Role [owner/officer/member] (default member): ").strip() or "member"
    status = input("Status [active/inactive] (default active): ").strip() or "active"
    title = input("Title (optional, e.g., President): ").strip() or None

    mem = Membership(personId=person.id, role=role, status=status, title=title)
    ref = club.reference.collection("memberships").document()
    ref.set(asdict(mem))
    print(f"Added membership: {ref.id}")

def list_memberships():
    _print_header("List Memberships in Club")
    club = _choose(list(db.collection("clubs").order_by("name").stream()), "club")
    if not club: return
    snaps = list(club.reference.collection("memberships").stream())
    for m in snaps:
        print(f"{m.id} :: {m.to_dict()}")
    return snaps

def update_membership():
    _print_header("Update Membership in Club")
    club = _choose(list(db.collection("clubs").order_by("name").stream()), "club")
    if not club: return
    mem = _choose(list(club.reference.collection("memberships").stream()), "membership")
    if not mem: return

    data = mem.to_dict()
    new_role = input(f"Role [owner/officer/member] (blank keep '{data.get('role')}'): ").strip() or data.get("role")
    new_status = input(f"Status [active/inactive] (blank keep '{data.get('status')}'): ").strip() or data.get("status")
    new_title = input(f"Title (blank keep '{data.get('title')}'): ").strip() or data.get("title")
    mem.reference.update({"role": new_role, "status": new_status, "title": new_title})
    print("Updated membership.")

def delete_membership():
    _print_header("Delete Membership in Club")
    club = _choose(list(db.collection("clubs").order_by("name").stream()), "club")
    if not club: return
    mem = _choose(list(club.reference.collection("memberships").stream()), "membership")
    if not mem: return
    confirm = input("Type DELETE to confirm: ").strip()
    if confirm == "DELETE":
        mem.reference.delete()
        print("Deleted membership.")
    else:
        print("Cancelled.")

# ── queries you’ll actually use
def list_club_members(club_id: str):
    print(f"\nMembers of club '{club_id}':")
    mems = list(db.collection("clubs").document(club_id).collection("memberships").stream())
    for m in mems:
        md = m.to_dict()
        person = db.collection("people").document(md["personId"]).get()
        print(f"- {person.to_dict().get('name','?')} ({md.get('role')}, {md.get('status')}) title={md.get('title')}")

# ── CLI menu
MENU = """
Choose an action:
  [U]niversity: 1) create  2) list  3) update  4) delete
  [C]lub:       5) create  6) list  7) update  8) delete
  [P]erson:     9) create 10) list 11) update 12) delete
  [M]embers:   13) add    14) list 15) update 16) delete
  [Q]uery:     17) list members of a club
  0) exit
> """

def main():
    while True:
        try:
            choice = input(MENU).strip()
        except EOFError:
            break

        if choice == "0":
            break
        elif choice == "1": create_university()
        elif choice == "2": list_universities()
        elif choice == "3": update_university()
        elif choice == "4": delete_university()
        elif choice == "5": create_club()
        elif choice == "6": list_clubs()
        elif choice == "7": update_club()
        elif choice == "8": delete_club()
        elif choice == "9": create_person()
        elif choice == "10": list_people()
        elif choice == "11": update_person()
        elif choice == "12": delete_person()
        elif choice == "13": add_membership()
        elif choice == "14": list_memberships()
        elif choice == "15": update_membership()
        elif choice == "16": delete_membership()
        elif choice == "17":
            club_id = input("Enter clubId: ").strip()
            if club_id:
                list_club_members(club_id)
        else:
            print("Unknown choice.")

if __name__ == "__main__":
    main()
