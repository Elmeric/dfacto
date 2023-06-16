import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple, Optional

from dfacto import settings as Config
from dfacto.util.basicpatterns import visitable

if TYPE_CHECKING:
    from dfacto.backend.schemas.invoice import Invoice

__all__ = [
    "Case",
    "TemplateType",
    "TokensDescription",
    "TokenTree",
    "TokenFamily",
    "TokenGenus",
    "Token",
    "NamingTemplate",
    "NamingTemplates",
]

logger = logging.getLogger(__name__)


class Case(Enum):
    ORIGINAL_CASE = "Original Case"
    UPPERCASE = "UPPERCASE"
    LOWERCASE = "lowercase"


class TemplateType(Enum):
    INVOICE = auto()
    DESTINATION = auto()


class FormatSpec(NamedTuple):
    name: str = ""
    spec: str = ""


@visitable
@dataclass()
class TokenNode:
    name: str
    not_allowed: dict[TemplateType, tuple[str, ...]] = field(init=False)

    def __post_init__(self) -> None:
        self.parent: Optional["TokenNode"] = None
        self.children: tuple["TokenNode", ...] = tuple()
        self.not_allowed = {
            TemplateType.INVOICE: (),
            TemplateType.DESTINATION: (),
        }

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def is_allowed(self, kind: TemplateType) -> bool:
        return self.name not in self.not_allowed[kind]


@dataclass()
class TokenTree(TokenNode):
    def __post_init__(self) -> None:
        self.tokens_by_name: dict[str, Token] = {}


@dataclass()
class TokenFamily(TokenNode):
    pass


@dataclass()
class TokenGenus(TokenNode):
    def __post_init__(self) -> None:
        self.not_allowed = {
            TemplateType.INVOICE: (),
            TemplateType.DESTINATION: ("Invoice code",),
        }


@dataclass()
class Token(TokenNode):
    genus_name: str
    format_spec: FormatSpec

    def as_text(self) -> str:
        if self.genus_name == "Free text":
            return self.name
        return f"<{self.name}>"

    def format(self, invoice: "Invoice") -> str:
        genus_name = self.genus_name

        # Date family
        if genus_name == "Invoice date":
            date_ = invoice.issued_on
            if date_ is None:
                date_ = datetime.now()
            fmt = self.format_spec.spec
            if fmt == "%Q":
                quarter = (date_.month - 1) // 3 + 1
                return f"Q{quarter}"
            return date_.strftime(fmt)

        # Invoice info family
        if genus_name == "Client name":
            client_name = invoice.client.name
            fmt = self.format_spec.spec
            if fmt == "%F":  # UPPERCASE
                client_name = client_name.upper()
            elif fmt == "%f":  # lowercase
                client_name = client_name.lower()
            return client_name

        if genus_name == "Invoice code":
            return f"FC{invoice.id:{self.format_spec.spec}}"

        # Free text token
        if genus_name == "Free text":
            return self.name

        # Default (should not be used)
        return ""


class TokensDescription:
    # pylint: disable=too-few-public-methods
    DATE_FORMATS = (
        FormatSpec("YYYYmmDD", "%Y%m%d"),
        FormatSpec("YYYY", "%Y"),
        FormatSpec("YY", "%y"),
        FormatSpec("Quarter", "%Q"),
        FormatSpec("Month", "%B"),
        FormatSpec("mm", "%m"),
        FormatSpec("DD", "%d"),
        FormatSpec("Weekday", "%j"),
    )
    NAME_FORMATS = (
        FormatSpec("Original Case", "%ff"),
        FormatSpec("UPPERCASE", "%F"),
        FormatSpec("lowercase", "%f"),
    )
    CODE_FORMATS = (
        FormatSpec("One digit", "01"),
        FormatSpec("Two digits", "02"),
        FormatSpec("Three digits", "03"),
        FormatSpec("Four digits", "04"),
        FormatSpec("Five digits", "05"),
        FormatSpec("Six digits", "06"),
    )

    TOKEN_FAMILIES = ("Date", "Invoice info")
    TOKEN_GENUS = {
        "Date": ("Invoice date",),
        "Invoice info": ("Client name", "Invoice code"),
    }

    TOKEN_FORMATS = {
        "Invoice date": DATE_FORMATS,
        "Client name": NAME_FORMATS,
        "Invoice code": CODE_FORMATS,
    }

    @classmethod
    def build_tokens_tree(cls) -> TokenTree:
        root = TokenTree("Tokens")
        tokens_by_name = {}
        families: list[TokenNode] = []
        for family_name in cls.TOKEN_FAMILIES:
            family = TokenFamily(family_name)
            family.parent = root
            families.append(family)
            genuses = []
            for genus_name in cls.TOKEN_GENUS[family_name]:
                genus = TokenGenus(genus_name)
                genus.parent = family
                genuses.append(genus)
                tokens = []
                for format_spec in cls.TOKEN_FORMATS[genus_name]:
                    token_name = f"{genus_name} ({format_spec[0]})"
                    token = Token(token_name, genus_name, format_spec)
                    tokens_by_name[token_name] = token
                    token.parent = genus
                    tokens.append(token)
                genus.children = tuple(tokens)
            family.children = tuple(genuses)
        root.children = tuple(families)
        root.tokens_by_name = tokens_by_name
        return root


class Boundary(NamedTuple):
    start: int
    end: int


@dataclass()
class NamingTemplate:
    key: str
    name: str
    template: tuple[Token, ...]

    def __post_init__(self) -> None:
        self.is_builtin = True

    def as_text(self) -> str:
        return "".join(token.as_text() for token in self.template)

    def boundaries(self) -> list[Boundary]:
        start = 0
        boundaries = []
        for token in self.template:
            end = start + len(token.as_text())
            boundaries.append(Boundary(start, end))
            start = end
        return boundaries

    def format(
        self,
        invoice: "Invoice",
        kind: TemplateType = TemplateType.INVOICE,  # pylint: disable=unused-argument
    ) -> str:
        return "".join(token.format(invoice) for token in self.template)
        # if kind == TemplateType.INVOICE:
        #     return "".join((name, ".pdf"))
        # else:
        #     assert kind == TemplateType.DESTINATION
        #     return name


class NamingTemplateDecoder(json.JSONDecoder):
    """A JSONDecoder to decode a NamingTemplate object in a JSON file."""

    def __init__(self) -> None:
        super().__init__(object_hook=self.naming_template_hook)

    @staticmethod
    def naming_template_hook(obj):  # type: ignore[no-untyped-def]
        if "__naming_template__" in obj:
            template = NamingTemplate(
                obj["key"],
                obj["name"],
                obj["template"],
            )
            template.is_builtin = False
            return template

        if "__token__" in obj:
            try:
                token = NamingTemplates.get_token(obj["name"])
            except KeyError:
                token = Token(obj["name"], "Free text", FormatSpec())
            return token

        if "__case__" in obj:
            return Case[obj["name"]]

        return obj


class NamingTemplateEncoder(json.JSONEncoder):
    """A JSONEncoder to encode a NamingTemplate object in a JSON file."""

    # pylint: disable-next=arguments-renamed
    def default(self, obj):  # type: ignore[no-untyped-def]
        """Overrides the JSONEncoder default encoding method.

        Non NamingTemplate objects are passed to the JSONEncoder base class, raising a
        TypeError if its type is not supported by the base encoder.

        Args:
            obj: the object to JSON encode.

        Returns:
             The string-encoded Path object.
        """
        if isinstance(obj, NamingTemplate):
            obj.__dict__.update({"__naming_template__": True})
            return obj.__dict__

        if isinstance(obj, Token):
            return {"__token__": True, "name": obj.name}

        if isinstance(obj, Case):
            return {"__case__": True, "name": obj.name}

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class NamingTemplates:
    # Build the tokens tree and keep its root node reference
    tokens_root_node = TokensDescription.build_tokens_tree()

    builtin_invoice_naming_templates = {
        "TPL_1": NamingTemplate(
            "TPL_1",
            "By Date - YYYYmmDD-Client_1-FC1234",
            (
                tokens_root_node.tokens_by_name["Invoice date (YYYYmmDD)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice code (One digit)"],
            ),
        ),
        "TPL_2": NamingTemplate(
            "TPL_2",
            "By Year and Month - YYYYmm-Client_1-FC1234",
            (
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
                tokens_root_node.tokens_by_name["Invoice date (mm)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice code (Four digits)"],
            ),
        ),
        "TPL_3": NamingTemplate(
            "TPL_3",
            "By Year - YYYY-Client_1-FC1234",
            (
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice code (One digit)"],
            ),
        ),
        "TPL_4": NamingTemplate(
            "TPL_4",
            "By Client name and date - Client_1-YYYYmmDD-FC1234",
            (
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice date (YYYYmmDD)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice code (One digit)"],
            ),
        ),
        "TPL_5": NamingTemplate(
            "TPL_5",
            "By Client name and year, month - Client_1-YYYYmm-FC1234",
            (
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
                tokens_root_node.tokens_by_name["Invoice date (mm)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice code (One digit)"],
            ),
        ),
        "TPL_6": NamingTemplate(
            "TPL_6",
            "By Client name and year - Client_1-YYYY-FC1234",
            (
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice code (One digit)"],
            ),
        ),
        "TPL_7": NamingTemplate(
            "TPL_7",
            "By Client name - Client_1-FC1234",
            (
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("-", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice code (One digit)"],
            ),
        ),
        "TPL_8": NamingTemplate(
            "TPL_8",
            "By invoice code - FC1234",
            (tokens_root_node.tokens_by_name["Invoice code (One digit)"],),
        ),
    }

    builtin_destination_naming_templates = {
        "TPL_1": NamingTemplate(
            "TPL_1",
            "By year, quarter and client name - YYYY/Qn/Client_1",
            (
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
                Token("/", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice date (Quarter)"],
                Token("/", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
            ),
        ),
        "TPL_2": NamingTemplate(
            "TPL_2",
            "By year and client name - YYYY/Client_1",
            (
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
                Token("/", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
            ),
        ),
        "TPL_3": NamingTemplate(
            "TPL_3",
            "By year - YYYY",
            (tokens_root_node.tokens_by_name["Invoice date (YYYY)"],),
        ),
        "TPL_4": NamingTemplate(
            "TPL_4",
            "By client name, year and quarter - Client_1/YYYY/Qn",
            (
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("/", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
                Token("/", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice date (Quarter)"],
            ),
        ),
        "TPL_5": NamingTemplate(
            "TPL_5",
            "By client name and year - Client_1/YYYY",
            (
                tokens_root_node.tokens_by_name["Client name (Original Case)"],
                Token("/", "Free text", FormatSpec()),
                tokens_root_node.tokens_by_name["Invoice date (YYYY)"],
            ),
        ),
        "TPL_6": NamingTemplate(
            "TPL_6",
            "By client name - Client_1",
            (tokens_root_node.tokens_by_name["Client name (Original Case)"],),
        ),
    }
    default_invoice_naming_template = "TPL_2"
    default_destination_naming_template = "TPL_2"

    def __init__(self) -> None:
        settings = Config.dfacto_settings
        self._templates_file = settings.app_dirs.user_config_dir / "templates.json"

        self.invoice, self.destination = self._load()

    @classmethod
    def get_token(cls, name: str) -> "Token":
        return cls.tokens_root_node.tokens_by_name[name]

    @classmethod
    def list_builtins(cls, kind: TemplateType) -> list[NamingTemplate]:
        if kind == TemplateType.INVOICE:
            return list(cls.builtin_invoice_naming_templates.values())
        assert kind == TemplateType.DESTINATION
        return list(cls.builtin_destination_naming_templates.values())

    def _load(self) -> tuple[dict[str, NamingTemplate], dict[str, NamingTemplate]]:
        try:
            with self._templates_file.open() as fh:
                templates = json.load(fh, cls=NamingTemplateDecoder)
                return templates["invoice"], templates["destination"]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("Cannot load custom naming templates: %s", e)
            return {}, {}

    def save(self) -> tuple[bool, str]:
        """Save the custom naming templates on a JSON file.

        Use a dedicated JSONEncoder to handle NamingTemplate and Token objects.

        Returns:
            A boolean status and associated error or success string message.
        """
        templates = {
            "invoice": self.invoice,
            "destination": self.destination,
        }
        try:
            with self._templates_file.open(mode="w") as fh:
                json.dump(templates, fh, indent=4, cls=NamingTemplateEncoder)
        except (OSError, TypeError) as e:
            msg = f"Cannot save custom naming templates: {e}"
            logger.warning(msg)
            return False, msg
        return True, "Custom naming templates successfully saved."

    def list_customs(self, kind: TemplateType) -> list[NamingTemplate]:
        if kind == TemplateType.INVOICE:
            return list(self.invoice.values())
        assert kind == TemplateType.DESTINATION
        return list(self.destination.values())

    def add(
        self, kind: TemplateType, name: str, template: tuple[Token, ...]
    ) -> NamingTemplate:
        key = f"TPL_{id(name)}"
        naming_template = NamingTemplate(key, name, template)
        naming_template.is_builtin = False
        if kind == TemplateType.INVOICE:
            self.invoice[key] = naming_template
        else:
            assert kind == TemplateType.DESTINATION
            self.destination[key] = naming_template
        return naming_template

    def delete(self, kind: TemplateType, template_key: str) -> None:
        if kind == TemplateType.INVOICE:
            del self.invoice[template_key]
        else:
            assert kind == TemplateType.DESTINATION
            del self.destination[template_key]

    def change(
        self, kind: TemplateType, template_key: str, template: tuple[Token, ...]
    ) -> NamingTemplate:
        if kind == TemplateType.INVOICE:
            naming_template = self.invoice[template_key]
        else:
            assert kind == TemplateType.DESTINATION
            naming_template = self.destination[template_key]
        naming_template.template = template
        return naming_template

    def get_by_key(self, kind: TemplateType, key: str) -> Optional[NamingTemplate]:
        if kind == TemplateType.INVOICE:
            try:
                template = NamingTemplates.builtin_invoice_naming_templates[key]
            except KeyError:
                try:
                    template = self.invoice[key]
                except KeyError:
                    template = None

        else:
            assert kind == TemplateType.DESTINATION
            try:
                template = NamingTemplates.builtin_destination_naming_templates[key]
            except KeyError:
                try:
                    template = self.destination[key]
                except KeyError:
                    template = None

        return template

    def get_default(self, kind: TemplateType) -> NamingTemplate:
        if kind == TemplateType.INVOICE:
            return self.builtin_invoice_naming_templates[
                self.default_invoice_naming_template
            ]
        assert kind == TemplateType.DESTINATION
        return self.builtin_destination_naming_templates[
            self.default_destination_naming_template
        ]
