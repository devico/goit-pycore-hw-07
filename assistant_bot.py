from collections import UserDict
from datetime import datetime, date, timedelta


class Field:
    """Базове поле запису (просто зберігає value)."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """Імʼя контакту (без додаткової валідації)."""
    pass


class Phone(Field):
    """
    Телефон — рівно 10 цифр (рядок із 10 цифр). Без нормалізації.
    """
    def __init__(self, value: str):
        self._validate(value)
        super().__init__(value)

    @staticmethod
    def _validate(value: str):
        if not isinstance(value, str):
            raise ValueError("Phone must be a string of 10 digits")
        if len(value) != 10 or not value.isdigit():
            raise ValueError("Phone must contain exactly 10 digits")

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, new_value: str):
        self._validate(new_value)
        self._value = new_value


class Birthday(Field):
    """Дата народження у форматі DD.MM.YYYY, зберігається як datetime.date."""
    def __init__(self, value: str):
        try:
            dt = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        self._value = dt

    @property
    def value(self) -> date:
        return self._value

    @value.setter
    def value(self, new_value):
        if isinstance(new_value, date):
            self._value = new_value
            return
        try:
            dt = datetime.strptime(str(new_value), "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        self._value = dt

    def __str__(self) -> str:
        return self._value.strftime("%d.%m.%Y")


class Record:
    """
    Запис:
    імʼя (Name),
    телефони (list[Phone]),
    день народження (Birthday | None).
    """
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.birthday: Birthday | None = None

    def add_phone(self, phone: str):
        """Додає телефон (рядок) до списку телефонів."""
        self.phones.append(Phone(phone))

    def remove_phone(self, phone: str):
        """
        Видаляє перший збіг номера phone, якщо він існує.
        """
        ph = self.find_phone(phone)
        if ph:
            self.phones.remove(ph)

    def edit_phone(self, old_phone: str, new_phone: str):
        """
        Замінює перший збіг old_phone на new_phone (валідація у Phone.value).
        """
        ph = self.find_phone(old_phone)
        if ph:
            ph.value = new_phone

    def find_phone(self, phone: str) -> str | None:
        """Повертає об'єкт Phone або None, якщо не знайдено."""
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    def add_birthday(self, birthday_str: str):
        """
        Додає/оновлює день народження. Формат DD.MM.YYYY.
        Може бути лише одне поле birthday.
        """
        self.birthday = Birthday(birthday_str)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones) if self.phones else ""
        bday = f", birthday: {self.birthday}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones}{bday}"


class AddressBook(UserDict):
    """Адресна книга: ключ — імʼя, значення — Record."""
    def add_record(self, record: Record):
        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        return self.data.get(name)

    def delete(self, name: str):
        self.data.pop(name, None)

    def get_upcoming_birthdays(self, today: date | None = None) -> list[str]:
        """
        Повертає список рядків: 'DD.MM.YYYY: name1, name2,...' для контактів,
        яких треба привітати протягом наступного тижня.
        Якщо ДН випадає на вихідні (сб/нд) — переносимо вітання на понеділок.
        """
        if today is None:
            today = date.today()

        end = today + timedelta(days=7)

        schedule: dict[date, list[str]] = {}

        for record in self.data.values():
            if not record.birthday:
                continue

            bday = record.birthday.value
            bday_this_year = bday.replace(year=today.year)
            if bday_this_year < today:
                bday_this_year = bday_this_year.replace(year=today.year + 1)

            if today < bday_this_year <= end:
                congratulate_day = bday_this_year
                if congratulate_day.weekday() == 5:
                    congratulate_day += timedelta(days=2)
                elif congratulate_day.weekday() == 6:
                    congratulate_day += timedelta(days=1)

                names = schedule.setdefault(congratulate_day, [])
                names.append(record.name.value)

        lines: list[str] = []
        for d in sorted(schedule.keys()):
            names = ", ".join(sorted(schedule[d]))
            lines.append(f"{d.strftime('%d.%m.%Y')}: {names}")
        return lines


def parse_input(user_input: str):
    """Розбирає рядок на команду та аргументи."""
    parts = user_input.split()
    if not parts:
        return "", []
    cmd, *args = parts
    return cmd.strip().lower(), args


def input_error(func):
    """
    Декоратор: перетворює типові помилки на дружні повідомлення,
    не зупиняючи роботу бота.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            return "Contact not found."
        except IndexError:
            return "Enter the argument for the command"
        except ValueError as e:
            return str(e) if str(e) else "Give me name and phone please."
    return wrapper


@input_error
def add_contact(args, book: AddressBook):
    """add [name] [phone] — додати контакт або телефон до існуючого."""
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_contact(args, book: AddressBook):
    """change [name] [old_phone] [new_phone] — замінити номер телефону."""
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    record.edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error
def show_phone(args, book: AddressBook):
    """phone [name] — показати телефони контакту."""
    (name,) = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    phones = ", ".join(p.value for p in record.phones) if record.phones else ""
    return phones or "No phones."


@input_error
def show_all(args, book: AddressBook):
    """all — показати всі контакти."""
    if not book.data:
        return ""
    return "\n".join(str(r) for r in book.data.values())


@input_error
def add_birthday(args, book: AddressBook):
    """add-birthday [name] [DD.MM.YYYY] — додати/оновити день народження."""
    name, bday, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
        msg = "Contact added."
    else:
        msg = "Birthday updated."
    record.add_birthday(bday)
    return msg


@input_error
def show_birthday(args, book: AddressBook):
    """show-birthday [name] — показати день народження контакту."""
    (name,) = args
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    if not record.birthday:
        return "No birthday set."
    return str(record.birthday)


@input_error
def birthdays(args, book: AddressBook):
    """birthdays — список вітать на наступний тиждень (по днях)."""
    lines = book.get_upcoming_birthdays()
    return "\n".join(lines) if lines else "No birthdays next week."


def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ("close", "exit"):
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_contact(args, book))

        elif command == "phone":
            print(show_phone(args, book))

        elif command == "all":
            print(show_all(args, book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
