from rest_framework import serializers as rfs
from rest_framework.exceptions import ValidationError

from api_app.analyzers_manager.models import AnalyzerConfig
from api_app.connectors_manager.models import ConnectorConfig
from api_app.models import Job, PythonModule
from api_app.pivots_manager.models import PivotConfig, PivotMap, PivotReport
from api_app.playbooks_manager.models import PlaybookConfig
from api_app.serializers.plugin import (
    PluginConfigSerializer,
    PythonConfigSerializer,
    PythonConfigSerializerForMigration,
)
from api_app.serializers.report import (
    AbstractReportBISerializer,
    AbstractReportSerializer,
)


class PivotReportSerializer(AbstractReportSerializer):
    class Meta:
        model = PivotReport
        fields = AbstractReportSerializer.Meta.fields
        list_serializer_class = AbstractReportSerializer.Meta.list_serializer_class


class PivotReportBISerializer(AbstractReportBISerializer):
    class Meta:
        model = PivotReport
        fields = AbstractReportBISerializer.Meta.fields
        list_serializer_class = AbstractReportBISerializer.Meta.list_serializer_class


class PivotMapSerializer(rfs.ModelSerializer):
    starting_job = rfs.PrimaryKeyRelatedField(queryset=Job.objects.all(), required=True)
    pivot_config = rfs.PrimaryKeyRelatedField(
        queryset=PivotConfig.objects.all(), required=True
    )
    ending_job = rfs.PrimaryKeyRelatedField(queryset=Job.objects.all(), required=True)

    class Meta:
        model = PivotMap
        fields = rfs.ALL_FIELDS

    def validate(self, attrs):
        result = super().validate(attrs)

        if (
            result["starting_job"].user.pk != self.context["request"].user.pk
            or result["ending_job"].user.pk != self.context["request"].user.pk
        ):
            raise ValidationError(
                {"detail": "You do not have permission to pivot these two jobs"}
            )
        return result


class PivotConfigSerializer(PythonConfigSerializer):
    playbooks_choice = rfs.SlugRelatedField(
        queryset=PlaybookConfig.objects.all(), slug_field="name", many=True
    )

    description = rfs.CharField(read_only=True)
    related_configs = rfs.SlugRelatedField(read_only=True, many=True, slug_field="name")
    related_analyzer_configs = rfs.SlugRelatedField(
        slug_field="name",
        queryset=AnalyzerConfig.objects.all(),
        many=True,
        required=False,
    )
    related_connector_configs = rfs.SlugRelatedField(
        slug_field="name",
        queryset=ConnectorConfig.objects.all(),
        many=True,
        required=False,
    )
    python_module = rfs.SlugRelatedField(
        queryset=PythonModule.objects.all(), slug_field="module"
    )
    plugin_config = rfs.DictField(write_only=True, required=False)

    class Meta:
        model = PivotConfig
        fields = rfs.ALL_FIELDS
        list_serializer_class = PythonConfigSerializer.Meta.list_serializer_class

    def validate(self, attrs):
        if "related_analyzer_configs" in attrs or "related_connector_configs" in attrs:
            related_analyzer_configs = attrs.get("related_analyzer_configs", [])
            related_connector_configs = attrs.get("related_connector_configs", [])
            if not related_analyzer_configs and not related_connector_configs:
                raise ValidationError(
                    {"detail": "No Analyzers and Connectors attached to pivot"}
                )
        return attrs

    def create(self, validated_data):
        plugin_config = validated_data.pop("plugin_config", {})
        pc = super().create(validated_data)

        # create plugin config
        if plugin_config:
            plugin_config_serializer = PluginConfigSerializer(
                data=plugin_config, context={"request": self.context["request"]}
            )
            plugin_config_serializer.is_valid(raise_exception=True)
            plugin_config_serializer.save()
        return pc


class PivotConfigSerializerForMigration(PythonConfigSerializerForMigration):
    related_analyzer_configs = rfs.SlugRelatedField(
        read_only=True, many=True, slug_field="name"
    )
    related_connector_configs = rfs.SlugRelatedField(
        read_only=True, many=True, slug_field="name"
    )
    playbooks_choice = rfs.SlugRelatedField(
        read_only=True, slug_field="name", many=True
    )

    class Meta:
        model = PivotConfig
        exclude = PythonConfigSerializerForMigration.Meta.exclude
