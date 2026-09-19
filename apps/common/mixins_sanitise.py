"""Shared sanitising behaviour for the two public submission forms."""
from rest_framework import serializers

from .sanitize import clean_line, clean_text, client_ip


class SanitisedSubmissionSerializer(serializers.ModelSerializer):
    """Scrubs submitted text and records the caller's address.

    Subclasses name which of their fields are single-line and which are
    bodies. Cleaning happens in validate() rather than per-field so that a
    field which cleans down to nothing still fails required-field validation
    instead of silently storing an empty string.
    """

    LINE_FIELDS: tuple[str, ...] = ()
    TEXT_FIELDS: tuple[str, ...] = ()
    REQUIRED_AFTER_CLEAN: tuple[str, ...] = ()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for name in self.LINE_FIELDS:
            if name in attrs:
                attrs[name] = clean_line(attrs[name])
        for name in self.TEXT_FIELDS:
            if name in attrs:
                attrs[name] = clean_text(attrs[name])

        empty = [n for n in self.REQUIRED_AFTER_CLEAN if not attrs.get(n)]
        if empty:
            raise serializers.ValidationError(
                {n: "This field cannot be blank." for n in empty}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("company_website", None)
        request = self.context.get("request")
        if request is not None:
            validated_data["source_ip"] = client_ip(request)
        return super().create(validated_data)
