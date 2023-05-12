import logging
import json
from typing import TYPE_CHECKING, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime

from dfacto.util.basicpatterns import visitable
from dfacto import settings as Config

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
    name: str
    spec: Optional[str]


@visitable
@dataclass()
class TokenNode:
    name: str
    notAllowed = {
        TemplateType.INVOICE: (),
        TemplateType.DESTINATION: (),
    }

    def __post_init__(self):
        self.parent: Optional["TokenNode"] = None
        self.children: tuple["TokenNode"] = tuple()

    @property
    def isLeaf(self) -> bool:
        return len(self.children) == 0

    def isAllowed(self, kind: TemplateType) -> bool:
        return self.name not in self.notAllowed[kind]


@dataclass()
class TokenTree(TokenNode):
    pass

    def __post_init__(self):
        self.tokensByName: dict[str, Token] = dict()


@dataclass()
class TokenFamily(TokenNode):
    notAllowed = {
        TemplateType.INVOICE: (),
        TemplateType.DESTINATION: (),
    }


@dataclass()
class TokenGenus(TokenNode):
    notAllowed = {
        TemplateType.INVOICE: (),
        TemplateType.DESTINATION: ("Invoice code",),
    }


@dataclass()
class Token(TokenNode):
    genusName: str
    formatSpec: Optional[FormatSpec]

    def asText(self):
        if self.genusName == "Free text":
            return self.name
        return f"<{self.name}>"

    def format(self, invoice: "Invoice") -> str:
        genusName = self.genusName

        # Date family
        if genusName == "Invoice date":
            date_ = invoice.issued_on
            if date_ is None:
                date_ = datetime.now()
            fmt = self.formatSpec.spec
            if fmt == "%Q":
                quarter = (date_.month - 1) // 3 + 1
                return f"Q{quarter}"
            return date_.strftime(fmt)

        # Invoice info family
        if genusName == "Client name":
            client_name = invoice.client.name
            fmt = self.formatSpec.spec
            if fmt == "%F":  # UPPERCASE
                client_name = client_name.upper()
            elif fmt == "%f":    # lowercase
                client_name = client_name.lower()
            return client_name

        if genusName == "Invoice code":
            return f"FC{invoice.id:{self.formatSpec.spec}}"

        # Free text token
        if genusName == "Free text":
            return self.name


class TokensDescription:
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
    def buildTokensTree(cls) -> TokenTree:
        root = TokenTree("Tokens")
        tokensByName = dict()
        families = list()
        for familyName in cls.TOKEN_FAMILIES:
            family = TokenFamily(familyName)
            family.parent = root
            families.append(family)
            genuses = list()
            for genusName in cls.TOKEN_GENUS[familyName]:
                genus = TokenGenus(genusName)
                genus.parent = family
                genuses.append(genus)
                tokens = list()
                for formatSpec in cls.TOKEN_FORMATS[genusName]:
                    tokenName = f"{genusName} ({formatSpec[0]})"
                    token = Token(tokenName, genusName, formatSpec)
                    tokensByName[tokenName] = token
                    token.parent = genus
                    tokens.append(token)
                genus.children = tuple(tokens)
            family.children = tuple(genuses)
        root.children = families
        root.tokensByName = tokensByName
        return root


class Boundary(NamedTuple):
    start: int
    end: int


@dataclass()
class NamingTemplate:
    key: str
    name: str
    template: tuple[Token, ...]

    def __post_init__(self):
        self.isBuiltin = True

    def asText(self) -> str:
        return "".join(token.asText() for token in self.template)

    def boundaries(self) -> list[Boundary]:
        start = 0
        boundaries = list()
        for token in self.template:
            end = start + len(token.asText())
            boundaries.append(Boundary(start, end))
            start = end
        return boundaries

    def format(
            self,
            invoice: "Invoice",
            kind: TemplateType = TemplateType.INVOICE
    ) -> str:
        return "".join(token.format(invoice) for token in self.template)
        # if kind == TemplateType.INVOICE:
        #     return "".join((name, ".pdf"))
        # else:
        #     assert kind == TemplateType.DESTINATION
        #     return name


class NamingTemplateDecoder(json.JSONDecoder):
    """A JSONDecoder to decode a NamingTemplate object in a JSON file.
    """
    def __init__(self):
        super().__init__(object_hook=self.namingTemplateHook)

    @staticmethod
    def namingTemplateHook(obj):
        if "__naming_template__" in obj:
            template = NamingTemplate(
                obj["key"],
                obj["name"],
                obj["template"],
            )
            template.isBuiltin = False
            return template

        if "__token__" in obj:
            try:
                token = NamingTemplates.getToken(obj["name"])
            except KeyError:
                token = Token(obj["name"], "Free text", None)
            return token

        if "__case__" in obj:
            return Case[obj["name"]]

        return obj


class NamingTemplateEncoder(json.JSONEncoder):
    """A JSONEncoder to encode a NamingTemplate object in a JSON file.
    """
    def default(self, obj):
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
    tokensRootNode = TokensDescription.buildTokensTree()

    builtinInvoiceNamingTemplates = {
        "TPL_1": NamingTemplate(
            "TPL_1",
            "By Date - YYYYmmDD-Client_1-FC1234",
            (
                tokensRootNode.tokensByName["Invoice date (YYYYmmDD)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice code (One digit)"],
            ),
        ),
        "TPL_2": NamingTemplate(
            "TPL_2",
            "By Year and Month - YYYYmm-Client_1-FC1234",
            (
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
                tokensRootNode.tokensByName["Invoice date (mm)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice code (Four digits)"],
            ),
        ),
        "TPL_3": NamingTemplate(
            "TPL_3",
            "By Year - YYYY-Client_1-FC1234",
            (
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice code (One digit)"],
            ),
        ),
        "TPL_4": NamingTemplate(
            "TPL_4",
            "By Client name and date - Client_1-YYYYmmDD-FC1234",
            (
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice date (YYYYmmDD)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice code (One digit)"],
            ),
        ),
        "TPL_5": NamingTemplate(
            "TPL_5",
            "By Client name and year, month - Client_1-YYYYmm-FC1234",
            (
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
                tokensRootNode.tokensByName["Invoice date (mm)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice code (One digit)"],
            ),
        ),
        "TPL_6": NamingTemplate(
            "TPL_6",
            "By Client name and year - Client_1-YYYY-FC1234",
            (
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice code (One digit)"],
            ),
        ),
        "TPL_7": NamingTemplate(
            "TPL_7",
            "By Client name - Client_1-FC1234",
            (
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("-", "Free text", None),
                tokensRootNode.tokensByName["Invoice code (One digit)"],
            ),
        ),
        "TPL_8": NamingTemplate(
            "TPL_8",
            "By invoice code - FC1234",
            (
                tokensRootNode.tokensByName["Invoice code (One digit)"],
            ),
        ),
    }

    builtinDestinationNamingTemplates = {
        "TPL_1": NamingTemplate(
            "TPL_1",
            "By year, quarter and client name - YYYY/Qn/Client_1",
            (
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
                Token("/", "Free text", None),
                tokensRootNode.tokensByName["Invoice date (Quarter)"],
                Token("/", "Free text", None),
                tokensRootNode.tokensByName["Client name (Original Case)"],
            ),
        ),
        "TPL_2": NamingTemplate(
            "TPL_2",
            "By year and client name - YYYY/Client_1",
            (
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
                Token("/", "Free text", None),
                tokensRootNode.tokensByName["Client name (Original Case)"],
            ),
        ),
        "TPL_3": NamingTemplate(
            "TPL_3",
            "By year - YYYY",
            (
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
            ),
        ),
        "TPL_4": NamingTemplate(
            "TPL_4",
            "By client name, year and quarter - Client_1/YYYY/Qn",
            (
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("/", "Free text", None),
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
                Token("/", "Free text", None),
                tokensRootNode.tokensByName["Invoice date (Quarter)"],
            ),
        ),
        "TPL_5": NamingTemplate(
            "TPL_5",
            "By client name and year - Client_1/YYYY",
            (
                tokensRootNode.tokensByName["Client name (Original Case)"],
                Token("/", "Free text", None),
                tokensRootNode.tokensByName["Invoice date (YYYY)"],
            ),
        ),
        "TPL_6": NamingTemplate(
            "TPL_6",
            "By client name - Client_1",
            (
                tokensRootNode.tokensByName["Client name (Original Case)"],
            ),
        ),
    }
    defaultInvoiceNamingTemplate = "TPL_2"
    defaultDestinationNamingTemplate = "TPL_2"

    def __init__(self):
        settings = Config.dfacto_settings
        self._templatesFile = settings.app_dirs.user_config_dir / "templates.json"

        self.invoice, self.destination = self._load()

    @classmethod
    def getToken(cls, name: str) -> "Token":
        return cls.tokensRootNode.tokensByName[name]

    @classmethod
    def listBuiltins(cls, kind: TemplateType) -> list[NamingTemplate]:
        if kind == TemplateType.INVOICE:
            return list(cls.builtinInvoiceNamingTemplates.values())
        else:
            assert kind == TemplateType.DESTINATION
            return list(cls.builtinDestinationNamingTemplates.values())

    def _load(self):
        try:
            with self._templatesFile.open() as fh:
                templates = json.load(fh, cls=NamingTemplateDecoder)
                return templates["invoice"], templates["destination"]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Cannot load custom naming templates: {e}")
            return dict(), dict()

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
            with self._templatesFile.open(mode="w") as fh:
                json.dump(templates, fh, indent=4, cls=NamingTemplateEncoder)
        except (OSError, TypeError) as e:
            msg = f"Cannot save custom naming templates: {e}"
            logger.warning(msg)
            return False, msg
        else:
            return True, "Custom naming templates successfully saved."

    def listCustoms(self, kind: TemplateType) -> list[NamingTemplate]:
        if kind == TemplateType.INVOICE:
            return list(self.invoice.values())
        else:
            assert kind == TemplateType.DESTINATION
            return list(self.destination.values())

    def add(
            self,
            kind: TemplateType,
            name: str, template: tuple[Token, ...]
    ) -> NamingTemplate:
        key = f"TPL_{id(name)}"
        namingTemplate = NamingTemplate(key, name, template)
        namingTemplate.isBuiltin = False
        if kind == TemplateType.INVOICE:
            self.invoice[key] = namingTemplate
        else:
            assert kind == TemplateType.DESTINATION
            self.destination[key] = namingTemplate
        return namingTemplate

    def delete(self, kind: TemplateType, templateKey: str) -> None:
        if kind == TemplateType.INVOICE:
            del self.invoice[templateKey]
        else:
            assert kind == TemplateType.DESTINATION
            del self.destination[templateKey]

    def change(
            self,
            kind: TemplateType,
            templateKey: str,
            template: tuple[Token, ...]
    ) -> NamingTemplate:
        if kind == TemplateType.INVOICE:
            namingTemplate = self.invoice[templateKey]
        else:
            assert kind == TemplateType.DESTINATION
            namingTemplate = self.destination[templateKey]
        namingTemplate.template = template
        return namingTemplate

    def getByKey(self, kind: TemplateType, key: str) -> Optional[NamingTemplate]:
        if kind == TemplateType.INVOICE:
            try:
                template = NamingTemplates.builtinInvoiceNamingTemplates[key]
            except KeyError:
                try:
                    template = self.invoice[key]
                except KeyError:
                    template = None

        else:
            assert kind == TemplateType.DESTINATION
            try:
                template = NamingTemplates.builtinDestinationNamingTemplates[key]
            except KeyError:
                try:
                    template = self.destination[key]
                except KeyError:
                    template = None

        return template

    def getDefault(self, kind: TemplateType) -> NamingTemplate:
        if kind == TemplateType.INVOICE:
            return self.builtinInvoiceNamingTemplates[self.defaultInvoiceNamingTemplate]
        else:
            assert kind == TemplateType.DESTINATION
            return self.builtinDestinationNamingTemplates[self.defaultDestinationNamingTemplate]
