from dataclasses import dataclass


@dataclass
class ValidationResult:
    valid: bool
    message: str


class DrawingValidator:

    @staticmethod
    def validate_extension(filename: str) -> ValidationResult:
        if not filename.lower().endswith(".dxf"):
            return ValidationResult(
                valid=False,
                message="Only .dxf files are supported.",
            )

        return ValidationResult(valid=True, message="OK")

    @staticmethod
    def validate_content(content: bytes) -> ValidationResult:
        if not content:
            return ValidationResult(
                valid=False,
                message="The uploaded file is empty.",
            )

        # Binary DXF files have a recognizable signature.
        if content.startswith(b"AutoCAD Binary DXF"):
            return ValidationResult(valid=True, message="OK")

        # ASCII DXF should be readable as text.
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("cp1252")
            except UnicodeDecodeError:
                return ValidationResult(
                    valid=False,
                    message="File is not a recognizable ASCII or binary DXF.",
                )

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in normalized.split("\n")]

        has_section = any(
            lines[i] == "0"
            and i + 1 < len(lines)
            and lines[i + 1].upper() == "SECTION"
            for i in range(len(lines) - 1)
        )

        has_eof = any(line.upper() == "EOF" for line in lines)

        if not has_section or not has_eof:
            return ValidationResult(
                valid=False,
                message="The file does not have the expected DXF structure.",
            )

        return ValidationResult(valid=True, message="OK")

    @classmethod
    def validate(
        cls,
        filename: str,
        content: bytes,
    ) -> ValidationResult:
        extension_result = cls.validate_extension(filename)

        if not extension_result.valid:
            return extension_result

        return cls.validate_content(content)