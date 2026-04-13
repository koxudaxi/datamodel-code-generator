#
#  Copyright MindBridge Analytics Inc. all rights reserved.
#
#  This material is confidential and may not be copied, distributed,
#  reversed engineered, decompiled or otherwise disseminated without
#  the prior written consent of MindBridge Analytics Inc.
#

from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Annotated, Any, Literal, Union
from pydantic import AwareDatetime, Field, RootModel
from mindbridgeapi.base_item import BaseItem

ObjectId = RootModel[str | None]


class WebhookPayloadType(str, Enum):
    """The event type that triggered the webhook."""

    EXPORT_READY = "export.ready"
    DATA_ADDED = "data.added"
    INGESTION_COMPLETE = "ingestion.complete"
    INGESTION_FAILED = "ingestion.failed"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    UNMAPPED_ACCOUNTS = "unmapped.accounts"
    ENGAGEMENT_CREATED = "engagement.created"
    ENGAGEMENT_UPDATED = "engagement.updated"
    ENGAGEMENT_DELETED = "engagement.deleted"
    ANALYSIS_CREATED = "analysis.created"
    ANALYSIS_UPDATED = "analysis.updated"
    ANALYSIS_DELETED = "analysis.deleted"
    ANALYSIS_ARCHIVED = "analysis.archived"
    ANALYSIS_UNARCHIVED = "analysis.unarchived"
    USER_INVITED = "user.invited"
    USER_STATUS = "user.status"
    USER_ROLE = "user.role"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"


class WebhookPayload(BaseItem):
    type: Annotated[
        WebhookPayloadType | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None


class AnalysisResultWebhookPayloadType(str, Enum):
    """The event type that triggered the webhook."""

    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"


class AnalysisWebhookData(BaseItem):
    engagement_id: Annotated[
        ObjectId | None,
        Field(
            alias="engagementId",
            description="The ID of the Engagement associated with the webhook event.",
        ),
    ] = None
    analysis_id: Annotated[
        ObjectId | None,
        Field(
            alias="analysisId",
            description="The ID of the Analysis associated with the webhook event.",
        ),
    ] = None


class AnalysisSourceWebhookPayloadType(str, Enum):
    """The event type that triggered the webhook."""

    INGESTION_COMPLETE = "ingestion.complete"
    INGESTION_FAILED = "ingestion.failed"


class AnalysisSourceWebhookData(BaseItem):
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    analysis_source_id: Annotated[
        ObjectId | None,
        Field(
            alias="analysisSourceId",
            description="The ID of the Analysis Source associated with the event.",
        ),
    ] = None
    analysis_id: Annotated[
        ObjectId | None,
        Field(
            alias="analysisId",
            description="The ID of the Analysis associated with the webhook event.",
        ),
    ] = None
    engagement_id: Annotated[
        ObjectId | None,
        Field(
            alias="engagementId",
            description="The ID of the Engagement associated with the webhook event.",
        ),
    ] = None


class AnalysisResultWebhookData(BaseItem):
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    analysis_id: Annotated[
        ObjectId | None,
        Field(
            alias="analysisId",
            description="The ID of the Analysis associated with the webhook event.",
        ),
    ] = None
    analysis_result_id: Annotated[
        ObjectId | None,
        Field(
            alias="analysisResultId",
            description="The ID of the Analysis Result associated with the webhook event.",
        ),
    ] = None
    engagement_id: Annotated[
        ObjectId | None,
        Field(
            alias="engagementId",
            description="The ID of the Engagement associated with the webhook event.",
        ),
    ] = None


class EngagementSubscriptionWebhookData(BaseItem):
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    engagement_id: Annotated[
        ObjectId | None,
        Field(
            alias="engagementId",
            description="The ID of the Engagement associated with the webhook event.",
        ),
    ] = None
    target_user_id: Annotated[
        ObjectId | None,
        Field(
            alias="targetUserId",
            description="The ID of the user associated with the webhook event.",
        ),
    ] = None


class EngagementWebhookPayloadType(str, Enum):
    """The event type that triggered the webhook."""

    ENGAGEMENT_CREATED = "engagement.created"
    ENGAGEMENT_UPDATED = "engagement.updated"
    ENGAGEMENT_DELETED = "engagement.deleted"


class EngagementWebhookData(BaseItem):
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    engagement_id: Annotated[
        ObjectId | None,
        Field(
            alias="engagementId",
            description="The ID of the Engagement associated with the webhook event.",
        ),
    ] = None


class FileManagerWebhookPayloadType(str, Enum):
    """The event type that triggered the webhook."""

    DATA_ADDED = "data.added"
    EXPORT_READY = "export.ready"


class FileManagerWebhookData(BaseItem):
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    file_manager_file_id: Annotated[
        ObjectId | None,
        Field(
            alias="fileManagerFileId",
            description="The ID of the data associated with the webhook event.",
        ),
    ] = None
    file_export_id: Annotated[
        ObjectId | None,
        Field(
            alias="fileExportId",
            description="The ID of the file export associated with the webhook event.",
        ),
    ] = None


class UserWebhookData(BaseItem):
    target_user_id: Annotated[
        ObjectId | None,
        Field(
            alias="targetUserId",
            description="The ID of the data associated with the webhook event.",
        ),
    ] = None


class UserRoleWebhookPayloadType(str, Enum):
    """The event type that triggered the webhook."""

    USER_INVITED = "user.invited"
    USER_ROLE = "user.role"


class UserRoleWebhookDataRole(str, Enum):
    """The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"""

    ROLE_ADMIN = "ROLE_ADMIN"
    ROLE_ORGANIZATION_ADMIN = "ROLE_ORGANIZATION_ADMIN"
    ROLE_USER = "ROLE_USER"
    ROLE_CLIENT = "ROLE_CLIENT"
    ROLE_MINDBRIDGE_SUPPORT = "ROLE_MINDBRIDGE_SUPPORT"
    ROLE_USER_ADMIN = "ROLE_USER_ADMIN"


class UserRoleWebhookData(BaseItem):
    role: Annotated[
        UserRoleWebhookDataRole | None,
        Field(
            description="The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"
        ),
    ] = None
    target_user_id: Annotated[
        ObjectId | None,
        Field(
            alias="targetUserId",
            description="The ID of the data associated with the webhook event.",
        ),
    ] = None


UserLoginWebhookData = RootModel[Any | None]


class UserStatusWebhookData(BaseItem):
    target_user_id: Annotated[
        ObjectId | None,
        Field(
            alias="targetUserId",
            description="The ID of the data associated with the webhook event.",
        ),
    ] = None
    status: Annotated[
        str | None,
        Field(
            description="Identifies the status change that triggered the webhook event."
        ),
    ] = None


class ApiWebhookUpdateEvent(str, Enum):
    EXPORT_READY = "EXPORT_READY"
    FILE_MANAGER_FILE_ADDED = "FILE_MANAGER_FILE_ADDED"
    INGESTION_COMPLETE = "INGESTION_COMPLETE"
    INGESTION_FAILED = "INGESTION_FAILED"
    INGESTION_ANALYSIS_COMPLETE = "INGESTION_ANALYSIS_COMPLETE"
    INGESTION_ANALYSIS_FAILED = "INGESTION_ANALYSIS_FAILED"
    UNMAPPED_ACCOUNTS_DETECTED = "UNMAPPED_ACCOUNTS_DETECTED"
    ENGAGEMENT_CREATED = "ENGAGEMENT_CREATED"
    ENGAGEMENT_UPDATED = "ENGAGEMENT_UPDATED"
    ENGAGEMENT_DELETED = "ENGAGEMENT_DELETED"
    ANALYSIS_CREATED = "ANALYSIS_CREATED"
    ANALYSIS_UPDATED = "ANALYSIS_UPDATED"
    ANALYSIS_DELETED = "ANALYSIS_DELETED"
    ANALYSIS_ARCHIVED = "ANALYSIS_ARCHIVED"
    ANALYSIS_UNARCHIVED = "ANALYSIS_UNARCHIVED"
    USER_INVITED = "USER_INVITED"
    USER_STATUS_UPDATED = "USER_STATUS_UPDATED"
    USER_ROLE_UPDATED = "USER_ROLE_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_LOGIN = "USER_LOGIN"


class ApiWebhookUpdateStatus(str, Enum):
    """The current status of the webhook."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ApiWebhookUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    name: Annotated[str | None, Field(description="The name of the webhook.")] = None
    url: Annotated[
        str | None,
        Field(description="The URL to which the webhook will send notifications."),
    ] = None
    technical_contact_id: Annotated[
        str | None,
        Field(
            alias="technicalContactId",
            description="A reference to an administrative user used to inform system administrators of issues with the webhooks.",
        ),
    ] = None
    events: Annotated[
        list[ApiWebhookUpdateEvent] | None,
        Field(
            description="A list of events that will trigger this webhook.",
            max_length=2147483647,
            min_length=1,
        ),
    ] = None
    status: Annotated[
        ApiWebhookUpdateStatus | None,
        Field(description="The current status of the webhook."),
    ] = None


class ApiUserInfoRead(BaseItem):
    user_id: Annotated[
        str | None, Field(alias="userId", description="Identifies the user.")
    ] = None
    user_name: Annotated[
        str | None, Field(alias="userName", description="The name of the user.")
    ] = None


class ApiWebhookReadEvent(str, Enum):
    EXPORT_READY = "EXPORT_READY"
    FILE_MANAGER_FILE_ADDED = "FILE_MANAGER_FILE_ADDED"
    INGESTION_COMPLETE = "INGESTION_COMPLETE"
    INGESTION_FAILED = "INGESTION_FAILED"
    INGESTION_ANALYSIS_COMPLETE = "INGESTION_ANALYSIS_COMPLETE"
    INGESTION_ANALYSIS_FAILED = "INGESTION_ANALYSIS_FAILED"
    UNMAPPED_ACCOUNTS_DETECTED = "UNMAPPED_ACCOUNTS_DETECTED"
    ENGAGEMENT_CREATED = "ENGAGEMENT_CREATED"
    ENGAGEMENT_UPDATED = "ENGAGEMENT_UPDATED"
    ENGAGEMENT_DELETED = "ENGAGEMENT_DELETED"
    ANALYSIS_CREATED = "ANALYSIS_CREATED"
    ANALYSIS_UPDATED = "ANALYSIS_UPDATED"
    ANALYSIS_DELETED = "ANALYSIS_DELETED"
    ANALYSIS_ARCHIVED = "ANALYSIS_ARCHIVED"
    ANALYSIS_UNARCHIVED = "ANALYSIS_UNARCHIVED"
    USER_INVITED = "USER_INVITED"
    USER_STATUS_UPDATED = "USER_STATUS_UPDATED"
    USER_ROLE_UPDATED = "USER_ROLE_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_LOGIN = "USER_LOGIN"


class ApiWebhookReadStatus(str, Enum):
    """The current status of the webhook."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ApiWebhookRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[AwareDatetime | None, Field(alias="creationDate")] = None
    last_modified_date: Annotated[
        AwareDatetime | None, Field(alias="lastModifiedDate")
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None, Field(alias="createdUserInfo")
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None, Field(alias="lastModifiedUserInfo")
    ] = None
    name: Annotated[str | None, Field(description="The name of the webhook.")] = None
    url: Annotated[
        str | None,
        Field(description="The URL to which the webhook will send notifications."),
    ] = None
    technical_contact_id: Annotated[
        str | None,
        Field(
            alias="technicalContactId",
            description="A reference to an administrative user used to inform system administrators of issues with the webhooks.",
        ),
    ] = None
    events: Annotated[
        list[ApiWebhookReadEvent] | None,
        Field(
            description="A list of events that will trigger this webhook.",
            max_length=2147483647,
            min_length=1,
        ),
    ] = None
    public_key: Annotated[
        str | None,
        Field(
            alias="publicKey",
            description="The public key used to verify the webhook signature.",
        ),
    ] = None
    status: Annotated[
        ApiWebhookReadStatus | None,
        Field(description="The current status of the webhook."),
    ] = None
    key_generation_timestamp: Annotated[
        AwareDatetime | None, Field(alias="keyGenerationTimestamp")
    ] = None


class ApiUserUpdateRole(str, Enum):
    """The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"""

    ROLE_ADMIN = "ROLE_ADMIN"
    ROLE_ORGANIZATION_ADMIN = "ROLE_ORGANIZATION_ADMIN"
    ROLE_USER = "ROLE_USER"
    ROLE_CLIENT = "ROLE_CLIENT"
    ROLE_MINDBRIDGE_SUPPORT = "ROLE_MINDBRIDGE_SUPPORT"
    ROLE_USER_ADMIN = "ROLE_USER_ADMIN"


class ApiUserUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    role: Annotated[
        ApiUserUpdateRole | None,
        Field(
            description="The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"
        ),
    ] = None
    enabled: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the user is enabled within this tenant."
        ),
    ] = None


class ApiLoginRecordRead(BaseItem):
    timestamp: Annotated[
        AwareDatetime | None,
        Field(
            description="The time when the user logged in or the API token was used."
        ),
    ] = None
    ip_address: Annotated[
        str | None,
        Field(
            alias="ipAddress",
            description="The IP address used when logging in or when making a request with an API token.",
        ),
    ] = None


class ApiUserReadRole(str, Enum):
    """The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"""

    ROLE_ADMIN = "ROLE_ADMIN"
    ROLE_ORGANIZATION_ADMIN = "ROLE_ORGANIZATION_ADMIN"
    ROLE_USER = "ROLE_USER"
    ROLE_CLIENT = "ROLE_CLIENT"
    ROLE_MINDBRIDGE_SUPPORT = "ROLE_MINDBRIDGE_SUPPORT"
    ROLE_USER_ADMIN = "ROLE_USER_ADMIN"


class ApiUserRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    first_name: Annotated[
        str | None, Field(alias="firstName", description="The user's first name.")
    ] = None
    last_name: Annotated[
        str | None, Field(alias="lastName", description="The user's last name.")
    ] = None
    email: Annotated[str | None, Field(description="The user's email address.")] = None
    role: Annotated[
        ApiUserReadRole | None,
        Field(
            description="The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"
        ),
    ] = None
    enabled: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the user is enabled within this tenant."
        ),
    ] = None
    validated: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the user has opened the account activation link after being created."
        ),
    ] = None
    service_account: Annotated[
        bool | None,
        Field(
            alias="serviceAccount",
            description="Indicates whether or not this account is used as part of an API token.",
        ),
    ] = None
    recent_logins: Annotated[
        list[ApiLoginRecordRead] | None,
        Field(
            alias="recentLogins",
            description="A list of the latest successful logins or token usage events by IP address.",
        ),
    ] = None


class ApiTaskUpdateStatus(str, Enum):
    """The current state of the task."""

    OPEN = "OPEN"
    NORMAL = "NORMAL"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class ApiTaskUpdateTaskApprovalStatus(str, Enum):
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"


class ApiTaskUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    status: Annotated[
        ApiTaskUpdateStatus | None,
        Field(description="The current state of the task.", title="Task Status"),
    ] = None
    assigned_id: Annotated[
        str | None,
        Field(
            alias="assignedId", description="Identifies the user assigned to this task."
        ),
    ] = None
    description: Annotated[
        str | None, Field(description="A description of the task.")
    ] = None
    sample: Annotated[
        str | None, Field(description="Which sample this task is a part of.")
    ] = None
    audit_areas: Annotated[
        list[str] | None,
        Field(
            alias="auditAreas",
            description="Which audit areas this task is associated with.",
        ),
    ] = None
    assertions: Annotated[
        list[str] | None,
        Field(description="Which assertions this task is associated with."),
    ] = None
    task_approval_status: Annotated[
        ApiTaskUpdateTaskApprovalStatus | None,
        Field(alias="taskApprovalStatus", title="Task Approval Status"),
    ] = None
    due_date: Annotated[date | None, Field(alias="dueDate")] = None
    approver_id: Annotated[str | None, Field(alias="approverId")] = None
    tags: list[str] | None = None


class ApiTaskCommentRead(BaseItem):
    comment_text: Annotated[
        str | None, Field(alias="commentText", description="The text of the comment.")
    ] = None
    captured: Annotated[
        AwareDatetime | None,
        Field(description="The timestamp when this comment was made."),
    ] = None
    author_id: Annotated[
        str | None,
        Field(
            alias="authorId",
            description="The unique identifier of the user who created this comment.",
        ),
    ] = None


class ApiTaskReadStatus(str, Enum):
    """The current state of the task."""

    OPEN = "OPEN"
    NORMAL = "NORMAL"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class ApiTaskReadType(str, Enum):
    """The type of entry this task is associated with."""

    ENTRY = "ENTRY"
    TRANSACTION = "TRANSACTION"
    AP_ENTRY = "AP_ENTRY"
    AR_ENTRY = "AR_ENTRY"
    AP_OUTSTANDING_ENTRY = "AP_OUTSTANDING_ENTRY"
    AR_OUTSTANDING_ENTRY = "AR_OUTSTANDING_ENTRY"
    TRA_ENTRY = "TRA_ENTRY"
    SUBLEDGER_ENTRY = "SUBLEDGER_ENTRY"


class ApiTaskReadSampleType(str, Enum):
    """The sampling method used to create this task."""

    RISK_BASED = "RISK_BASED"
    RANDOM = "RANDOM"
    MANUAL = "MANUAL"
    MONETARY_UNIT_SAMPLING = "MONETARY_UNIT_SAMPLING"


class ApiTaskReadTaskApprovalStatus(str, Enum):
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"


class MoneyRead(BaseItem):
    amount: int | None = None
    currency: str | None = None


class ApiFilterAccountConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterAccountSelection(BaseItem):
    name: Annotated[
        str | None, Field(description="The display name of the account being selected.")
    ] = None
    code: Annotated[
        str | None,
        Field(
            description="The account grouping code or account ID of the selected account."
        ),
    ] = None
    use_account_id: Annotated[
        bool | None,
        Field(
            alias="useAccountId",
            description="If `true` then the selected account will be identified by the account ID rather than the grouping code.",
        ),
    ] = None


class ApiFilterComplexMonetaryFlowConditionApiFilterComplexMonetaryFlowCondition(
    BaseItem
):
    type: Annotated[
        Literal["MONETARY_FLOW"] | None, Field(title="Filter Condition Type")
    ] = "MONETARY_FLOW"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_flow_type: Annotated[
        Literal["COMPLEX_FLOW"] | None,
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ] = "COMPLEX_FLOW"


class ApiFilterConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterConditionUpdateType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterControlPointConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterControlPointConditionRiskLevel(str, Enum):
    """The risk level of the selected control points."""

    HIGH_RISK = "HIGH_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    LOW_RISK = "LOW_RISK"


class ApiFilterControlPointSelection(BaseItem):
    id: Annotated[
        str | None, Field(description="The ID of the selected control point.")
    ] = None
    name: Annotated[
        str | None, Field(description="The display name of the control point.")
    ] = None
    symbolic_name: Annotated[
        str | None,
        Field(
            alias="symbolicName",
            description="The symbolic name of the target control point. For custom control points this is the symbolic name of the control point it is based on.",
        ),
    ] = None
    rules_based: Annotated[bool | None, Field(alias="rulesBased")] = None


class ApiFilterDateConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterDateConditionDateType(str, Enum):
    """The type of date condition."""

    BEFORE = "BEFORE"
    AFTER = "AFTER"
    SPECIFIC_VALUE = "SPECIFIC_VALUE"
    BETWEEN = "BETWEEN"


class ApiFilterDateConditionApiFilterDateCondition13(BaseItem):
    type: Annotated[
        Literal["DATE"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "DATE"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    date_type: Annotated[
        ApiFilterDateConditionDateType | None,
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ] = None


class ApiFilterDateRangeConditionApiFilterDateRangeCondition(BaseItem):
    type: Annotated[Literal["DATE"] | None, Field(title="Filter Condition Type")] = (
        "DATE"
    )
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    date_type: Annotated[
        Literal["BETWEEN"] | None, Field(alias="dateType", title="Filter Date Type")
    ] = "BETWEEN"
    range_start: Annotated[
        date | None,
        Field(
            alias="rangeStart",
            description="The start of an ISO date range to compare entries to.",
        ),
    ] = None
    range_end: Annotated[
        date | None,
        Field(
            alias="rangeEnd",
            description="The end of an ISO date range to compare entries to.",
        ),
    ] = None


class ApiFilterDateValueConditionDateType(str, Enum):
    AFTER = "AFTER"
    BEFORE = "BEFORE"
    SPECIFIC_VALUE = "SPECIFIC_VALUE"


class ApiFilterDateValueConditionApiFilterDateValueCondition(BaseItem):
    type: Annotated[Literal["DATE"] | None, Field(title="Filter Condition Type")] = (
        "DATE"
    )
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    date_type: Annotated[
        ApiFilterDateValueConditionDateType | None,
        Field(alias="dateType", title="Filter Date Type"),
    ] = None
    value: Annotated[
        date | None, Field(description="An ISO date value to compare entries to.")
    ] = None


class ApiFilterGroupConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterGroupConditionOperator(str, Enum):
    """The operator to be applied to conditions within this group."""

    AND = "AND"
    OR = "OR"


class ApiFilterGroupConditionUpdateType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterGroupConditionUpdateOperator(str, Enum):
    """The operator to be applied to conditions within this group."""

    AND = "AND"
    OR = "OR"


class ApiFilterMaterialityConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterMaterialityConditionMaterialityOption(str, Enum):
    """The type of materiality comparison."""

    ABOVE = "ABOVE"
    BELOW = "BELOW"
    PERCENTAGE = "PERCENTAGE"


class ApiFilterMaterialityConditionApiFilterMaterialityCondition13(BaseItem):
    type: Annotated[
        Literal["MATERIALITY"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "MATERIALITY"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    materiality_option: Annotated[
        ApiFilterMaterialityConditionMaterialityOption | None,
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ] = None


class ApiFilterMaterialityOptionConditionMaterialityOption(str, Enum):
    ABOVE = "ABOVE"
    BELOW = "BELOW"


class ApiFilterMaterialityOptionConditionApiFilterMaterialityOptionCondition(BaseItem):
    type: Annotated[
        Literal["MATERIALITY"] | None, Field(title="Filter Condition Type")
    ] = "MATERIALITY"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    materiality_option: Annotated[
        ApiFilterMaterialityOptionConditionMaterialityOption | None,
        Field(alias="materialityOption", title="Filter Materiality Value Options"),
    ] = None


class ApiFilterMaterialityValueConditionApiFilterMaterialityValueCondition(BaseItem):
    type: Annotated[
        Literal["MATERIALITY"] | None, Field(title="Filter Condition Type")
    ] = "MATERIALITY"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    materiality_option: Annotated[
        Literal["PERCENTAGE"] | None,
        Field(alias="materialityOption", title="Filter Materiality Value Options"),
    ] = "PERCENTAGE"
    value: Annotated[
        float | None,
        Field(
            description="The percentage value, as a decimal number, with 100.00 being 100%."
        ),
    ] = None


class ApiFilterMonetaryFlowConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterMonetaryFlowConditionMonetaryFlowType(str, Enum):
    """The type of monetary flow this filter will match."""

    SIMPLE_FLOW = "SIMPLE_FLOW"
    COMPLEX_FLOW = "COMPLEX_FLOW"
    SPECIFIC_FLOW = "SPECIFIC_FLOW"


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13(BaseItem):
    type: Annotated[
        Literal["MONETARY_FLOW"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "MONETARY_FLOW"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_flow_type: Annotated[
        ApiFilterMonetaryFlowConditionMonetaryFlowType | None,
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ] = None


class ApiFilterMonetaryValueConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterMonetaryValueConditionMonetaryValueType(str, Enum):
    """The type of monetary value condition."""

    MORE_THAN = "MORE_THAN"
    LESS_THAN = "LESS_THAN"
    SPECIFIC_VALUE = "SPECIFIC_VALUE"
    BETWEEN = "BETWEEN"


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13(BaseItem):
    type: Annotated[
        Literal["MONEY"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "MONEY"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_value_type: Annotated[
        ApiFilterMonetaryValueConditionMonetaryValueType | None,
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ] = None


class ApiFilterMonetaryValueRangeConditionApiFilterMonetaryValueRangeCondition(
    BaseItem
):
    type: Annotated[Literal["MONEY"] | None, Field(title="Filter Condition Type")] = (
        "MONEY"
    )
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_value_type: Annotated[
        Literal["BETWEEN"] | None,
        Field(alias="monetaryValueType", title="Filter Monetary Type"),
    ] = "BETWEEN"
    range_start: Annotated[
        int | None,
        Field(
            alias="rangeStart",
            description="The start of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ] = None
    range_end: Annotated[
        int | None,
        Field(
            alias="rangeEnd",
            description="The end of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ] = None


class ApiFilterMonetaryValueValueConditionMonetaryValueType(str, Enum):
    MORE_THAN = "MORE_THAN"
    SPECIFIC_VALUE = "SPECIFIC_VALUE"
    LESS_THAN = "LESS_THAN"


class ApiFilterMonetaryValueValueConditionApiFilterMonetaryValueValueCondition(
    BaseItem
):
    type: Annotated[Literal["MONEY"] | None, Field(title="Filter Condition Type")] = (
        "MONEY"
    )
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_value_type: Annotated[
        ApiFilterMonetaryValueValueConditionMonetaryValueType | None,
        Field(alias="monetaryValueType", title="Filter Monetary Type"),
    ] = None
    value: Annotated[
        int | None,
        Field(description="The MONEY_100 formatted number to compare with entries."),
    ] = None


class ApiFilterNumericalValueConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterNumericalValueConditionNumericalValueType(str, Enum):
    """The type of numerical value condition."""

    MORE_THAN = "MORE_THAN"
    LESS_THAN = "LESS_THAN"
    SPECIFIC_VALUE = "SPECIFIC_VALUE"
    BETWEEN = "BETWEEN"


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13(BaseItem):
    type: Annotated[
        Literal["NUMERICAL"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "NUMERICAL"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    numerical_value_type: Annotated[
        ApiFilterNumericalValueConditionNumericalValueType | None,
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ] = None


class ApiFilterNumericalValueRangeConditionApiFilterNumericalValueRangeCondition(
    BaseItem
):
    type: Annotated[
        Literal["NUMERICAL"] | None, Field(title="Filter Condition Type")
    ] = "NUMERICAL"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    numerical_value_type: Annotated[
        Literal["BETWEEN"] | None,
        Field(alias="numericalValueType", title="Filter Numerical Value Type"),
    ] = "BETWEEN"
    range_start: Annotated[
        int | None,
        Field(
            alias="rangeStart",
            description="The start value of a range to compare entries to.",
        ),
    ] = None
    range_end: Annotated[
        int | None,
        Field(
            alias="rangeEnd",
            description="The end value of a range to compare entries to.",
        ),
    ] = None


class ApiFilterNumericalValueValueConditionNumericalValueType(str, Enum):
    MORE_THAN = "MORE_THAN"
    SPECIFIC_VALUE = "SPECIFIC_VALUE"
    LESS_THAN = "LESS_THAN"


class ApiFilterNumericalValueValueConditionApiFilterNumericalValueValueCondition(
    BaseItem
):
    type: Annotated[
        Literal["NUMERICAL"] | None, Field(title="Filter Condition Type")
    ] = "NUMERICAL"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    numerical_value_type: Annotated[
        ApiFilterNumericalValueValueConditionNumericalValueType | None,
        Field(alias="numericalValueType", title="Filter Numerical Value Type"),
    ] = None
    value: Annotated[
        int | None, Field(description="A value to compare entries to.")
    ] = None


class ApiFilterPopulationsConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterPopulationsConditionApiFilterPopulationsCondition13(BaseItem):
    type: Annotated[
        Literal["POPULATIONS"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "POPULATIONS"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    population_ids: Annotated[
        list[str] | None,
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ] = None


class ApiFilterRiskScoreConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterRiskScoreConditionRiskScoreType(str, Enum):
    """Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage."""

    PERCENT = "PERCENT"
    HML = "HML"


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13(BaseItem):
    type: Annotated[
        Literal["RISK_SCORE"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "RISK_SCORE"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    risk_score_type: Annotated[
        ApiFilterRiskScoreConditionRiskScoreType | None,
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ] = None
    risk_score_id: Annotated[
        str | None,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ] = None
    risk_score_label: Annotated[
        str | None,
        Field(
            alias="riskScoreLabel",
            description="The display name of the risk score being filtered.",
        ),
    ] = None


class ApiFilterRiskScoreHMLConditionValue(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNSCORED = "UNSCORED"


class ApiFilterRiskScoreHMLConditionApiFilterRiskScoreHMLCondition(BaseItem):
    type: Annotated[
        Literal["RISK_SCORE"] | None, Field(title="Filter Condition Type")
    ] = "RISK_SCORE"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    risk_score_type: Annotated[
        Literal["HML"] | None,
        Field(alias="riskScoreType", title="Filter Risk Score Type"),
    ] = "HML"
    risk_score_id: Annotated[str | None, Field(alias="riskScoreId")] = None
    risk_score_label: Annotated[str | None, Field(alias="riskScoreLabel")] = None
    values: Annotated[
        list[ApiFilterRiskScoreHMLConditionValue] | None,
        Field(description="A list of HML options to include in the filter."),
    ] = None


class ApiFilterRiskScorePercentConditionRiskScorePercentType(str, Enum):
    """Determines the type of risk score percent condition to filter."""

    MORE_THAN = "MORE_THAN"
    LESS_THAN = "LESS_THAN"
    BETWEEN = "BETWEEN"
    CUSTOM_RANGE = "CUSTOM_RANGE"
    UNSCORED = "UNSCORED"


class ApiFilterRiskScorePercentConditionApiFilterRiskScorePercentCondition(BaseItem):
    type: Annotated[
        Literal["RISK_SCORE"] | None, Field(title="Filter Condition Type")
    ] = "RISK_SCORE"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    risk_score_type: Annotated[
        Literal["PERCENT"] | None,
        Field(alias="riskScoreType", title="Filter Risk Score Type"),
    ] = "PERCENT"
    risk_score_id: Annotated[str | None, Field(alias="riskScoreId")] = None
    risk_score_label: Annotated[str | None, Field(alias="riskScoreLabel")] = None
    risk_score_percent_type: Annotated[
        ApiFilterRiskScorePercentConditionRiskScorePercentType | None,
        Field(
            alias="riskScorePercentType",
            description="Determines the type of risk score percent condition to filter.",
            title="Filter Risk Score Percent Type",
        ),
    ] = None


class ApiFilterRiskScorePercentRangeConditionRiskScorePercentType(str, Enum):
    BETWEEN = "BETWEEN"
    CUSTOM_RANGE = "CUSTOM_RANGE"


class ApiFilterRiskScorePercentRangeConditionApiFilterRiskScorePercentRangeCondition(
    BaseItem
):
    type: Annotated[
        Literal["RISK_SCORE"] | None, Field(title="Filter Condition Type")
    ] = "RISK_SCORE"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    risk_score_type: Annotated[
        Literal["PERCENT"] | None,
        Field(alias="riskScoreType", title="Filter Risk Score Type"),
    ] = "PERCENT"
    risk_score_id: Annotated[str | None, Field(alias="riskScoreId")] = None
    risk_score_label: Annotated[str | None, Field(alias="riskScoreLabel")] = None
    risk_score_percent_type: Annotated[
        ApiFilterRiskScorePercentRangeConditionRiskScorePercentType | None,
        Field(alias="riskScorePercentType", title="Filter Risk Score Percent Type"),
    ] = None
    range_start: Annotated[
        int | None,
        Field(
            alias="rangeStart",
            description="The start of the number range between 0 and 10,000.",
        ),
    ] = None
    range_end: Annotated[
        int | None,
        Field(
            alias="rangeEnd",
            description="The end of the number range between 0 and 10,000.",
        ),
    ] = None


class ApiFilterRiskScorePercentUnscoredConditionApiFilterRiskScorePercentUnscoredCondition(
    BaseItem
):
    type: Annotated[
        Literal["RISK_SCORE"] | None, Field(title="Filter Condition Type")
    ] = "RISK_SCORE"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    risk_score_type: Annotated[
        Literal["PERCENT"] | None,
        Field(alias="riskScoreType", title="Filter Risk Score Type"),
    ] = "PERCENT"
    risk_score_id: Annotated[str | None, Field(alias="riskScoreId")] = None
    risk_score_label: Annotated[str | None, Field(alias="riskScoreLabel")] = None
    risk_score_percent_type: Annotated[
        Literal["UNSCORED"] | None,
        Field(alias="riskScorePercentType", title="Filter Risk Score Percent Type"),
    ] = "UNSCORED"


class ApiFilterRiskScorePercentValueConditionRiskScorePercentType(str, Enum):
    MORE_THAN = "MORE_THAN"
    LESS_THAN = "LESS_THAN"


class ApiFilterRiskScorePercentValueConditionApiFilterRiskScorePercentValueCondition(
    BaseItem
):
    type: Annotated[
        Literal["RISK_SCORE"] | None, Field(title="Filter Condition Type")
    ] = "RISK_SCORE"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    risk_score_type: Annotated[
        Literal["PERCENT"] | None,
        Field(alias="riskScoreType", title="Filter Risk Score Type"),
    ] = "PERCENT"
    risk_score_id: Annotated[str | None, Field(alias="riskScoreId")] = None
    risk_score_label: Annotated[str | None, Field(alias="riskScoreLabel")] = None
    risk_score_percent_type: Annotated[
        ApiFilterRiskScorePercentValueConditionRiskScorePercentType | None,
        Field(alias="riskScorePercentType", title="Filter Risk Score Percent Type"),
    ] = None
    value: Annotated[
        int | None,
        Field(
            description="A number between 0 and 10,000 used as part of a more than, or less than filter."
        ),
    ] = None


class ApiFilterSimpleMonetaryFlowConditionApiFilterSimpleMonetaryFlowCondition(
    BaseItem
):
    type: Annotated[
        Literal["MONETARY_FLOW"] | None, Field(title="Filter Condition Type")
    ] = "MONETARY_FLOW"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_flow_type: Annotated[
        Literal["SIMPLE_FLOW"] | None,
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ] = "SIMPLE_FLOW"


class ApiFilterSpecificMonetaryFlowConditionSpecificMonetaryFlowType(str, Enum):
    """The type of specific monetary flow."""

    SPECIFIC_VALUE = "SPECIFIC_VALUE"
    MORE_THAN = "MORE_THAN"
    BETWEEN = "BETWEEN"


class ApiFilterSpecificMonetaryFlowConditionApiFilterSpecificMonetaryFlowCondition(
    BaseItem
):
    type: Annotated[
        Literal["MONETARY_FLOW"] | None, Field(title="Filter Condition Type")
    ] = "MONETARY_FLOW"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_flow_type: Annotated[
        Literal["SPECIFIC_FLOW"] | None,
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ] = "SPECIFIC_FLOW"
    credit_account: Annotated[
        ApiFilterAccountSelection | None,
        Field(
            alias="creditAccount",
            description="The selected credit account in the monetary flow.",
        ),
    ] = None
    debit_account: Annotated[
        ApiFilterAccountSelection | None,
        Field(
            alias="debitAccount",
            description="The selected debit account in the monetary flow.",
        ),
    ] = None
    specific_monetary_flow_type: Annotated[
        ApiFilterSpecificMonetaryFlowConditionSpecificMonetaryFlowType | None,
        Field(
            alias="specificMonetaryFlowType",
            description="The type of specific monetary flow.",
            title="Filter Specific Monetary Flow Type",
        ),
    ] = None


class ApiFilterSpecificMonetaryFlowRangeConditionApiFilterSpecificMonetaryFlowRangeCondition(
    BaseItem
):
    type: Annotated[
        Literal["MONETARY_FLOW"] | None, Field(title="Filter Condition Type")
    ] = "MONETARY_FLOW"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_flow_type: Annotated[
        Literal["SPECIFIC_FLOW"] | None,
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ] = "SPECIFIC_FLOW"
    credit_account: Annotated[
        ApiFilterAccountSelection | None, Field(alias="creditAccount")
    ] = None
    debit_account: Annotated[
        ApiFilterAccountSelection | None, Field(alias="debitAccount")
    ] = None
    specific_monetary_flow_type: Annotated[
        Literal["BETWEEN"] | None,
        Field(
            alias="specificMonetaryFlowType", title="Filter Specific Monetary Flow Type"
        ),
    ] = "BETWEEN"
    range_start: Annotated[
        int | None,
        Field(
            alias="rangeStart",
            description="The start of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ] = None
    range_end: Annotated[
        int | None,
        Field(
            alias="rangeEnd",
            description="The end of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ] = None


class ApiFilterSpecificMonetaryFlowValueConditionSpecificMonetaryFlowType(str, Enum):
    SPECIFIC_VALUE = "SPECIFIC_VALUE"
    MORE_THAN = "MORE_THAN"


class ApiFilterSpecificMonetaryFlowValueConditionApiFilterSpecificMonetaryFlowValueCondition(
    BaseItem
):
    type: Annotated[
        Literal["MONETARY_FLOW"] | None, Field(title="Filter Condition Type")
    ] = "MONETARY_FLOW"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    monetary_flow_type: Annotated[
        Literal["SPECIFIC_FLOW"] | None,
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ] = "SPECIFIC_FLOW"
    credit_account: Annotated[
        ApiFilterAccountSelection | None, Field(alias="creditAccount")
    ] = None
    debit_account: Annotated[
        ApiFilterAccountSelection | None, Field(alias="debitAccount")
    ] = None
    specific_monetary_flow_type: Annotated[
        ApiFilterSpecificMonetaryFlowValueConditionSpecificMonetaryFlowType | None,
        Field(
            alias="specificMonetaryFlowType", title="Filter Specific Monetary Flow Type"
        ),
    ] = None
    value: Annotated[
        int | None,
        Field(description="The MONEY_100 formatted number to compare with entries."),
    ] = None


class ApiFilterStringArrayConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterStringArrayConditionApiFilterStringArrayCondition13(BaseItem):
    type: Annotated[
        Literal["STRING_ARRAY"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "STRING_ARRAY"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    values: Annotated[
        list[str] | None,
        Field(description="The set of text values used to filter entries."),
    ] = None


class ApiFilterStringConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterStringConditionApiFilterStringCondition13(BaseItem):
    type: Annotated[
        Literal["STRING"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "STRING"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    value: Annotated[
        str | None, Field(description="The text value used to filter entries.")
    ] = None


class ApiFilterTypeaheadEntryConditionType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterUpdateFilterType(str, Enum):
    """The type of this filter. Determines in which context analyses can access it."""

    LIBRARY = "LIBRARY"
    ORGANIZATION = "ORGANIZATION"
    PRIVATE = "PRIVATE"
    ENGAGEMENT = "ENGAGEMENT"


class ApiTypeaheadEntry(BaseItem):
    lookup_id: Annotated[
        str | None,
        Field(alias="lookupId", description="The identifier of the selected entry."),
    ] = None
    display_name: Annotated[
        str | None,
        Field(
            alias="displayName", description="The display name of the selected entry."
        ),
    ] = None
    hide_lookup_id: Annotated[
        bool | None,
        Field(
            alias="hideLookupId",
            description="If `false` then the entry will be displayed with both the lookup ID and the display name. If `true` then only the display name will be used when displaying this entry.",
        ),
    ] = None


class ApiFilterConditionReadType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterGroupConditionReadType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterGroupConditionReadOperator(str, Enum):
    """The operator to be applied to conditions within this group."""

    AND = "AND"
    OR = "OR"


class ApiFilterReadFilterType(str, Enum):
    """The type of this filter. Determines in which context analyses can access it."""

    LIBRARY = "LIBRARY"
    ORGANIZATION = "ORGANIZATION"
    PRIVATE = "PRIVATE"
    ENGAGEMENT = "ENGAGEMENT"


class ApiFilterReadDataType(str, Enum):
    """The intended data type for this filter."""

    TRANSACTIONS = "TRANSACTIONS"
    ENTRIES = "ENTRIES"
    LIBRARY = "LIBRARY"


class ApiRiskRangeBoundsUpdate(BaseItem):
    low_threshold: Annotated[
        int | None,
        Field(
            alias="lowThreshold",
            description="The low threshold of the risk range.",
            ge=0,
            le=10000,
        ),
    ] = None
    high_threshold: Annotated[
        int | None,
        Field(
            alias="highThreshold",
            description="The high threshold of the risk range.",
            ge=0,
            le=10000,
        ),
    ] = None


class ApiRiskRangesUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    low: Annotated[
        ApiRiskRangeBoundsUpdate | None, Field(description="The low range bounds.")
    ] = None
    medium: Annotated[
        ApiRiskRangeBoundsUpdate | None, Field(description="The medium range bounds.")
    ] = None
    high: Annotated[
        ApiRiskRangeBoundsUpdate | None, Field(description="The high range bounds.")
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the risk range.", max_length=80, min_length=0),
    ] = None
    description: Annotated[
        str | None,
        Field(
            description="The description of the risk range.",
            max_length=250,
            min_length=0,
        ),
    ] = None


class ApiRiskRangeBoundsRead(BaseItem):
    low_threshold: Annotated[
        int | None,
        Field(
            alias="lowThreshold",
            description="The low threshold of the risk range.",
            ge=0,
            le=10000,
        ),
    ] = None
    high_threshold: Annotated[
        int | None,
        Field(
            alias="highThreshold",
            description="The high threshold of the risk range.",
            ge=0,
            le=10000,
        ),
    ] = None


class ApiRiskRangesRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    low: Annotated[
        ApiRiskRangeBoundsRead | None, Field(description="The low range bounds.")
    ] = None
    medium: Annotated[
        ApiRiskRangeBoundsRead | None, Field(description="The medium range bounds.")
    ] = None
    high: Annotated[
        ApiRiskRangeBoundsRead | None, Field(description="The high range bounds.")
    ] = None
    system: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the risk ranges are a MindBridge system risk range."
        ),
    ] = None
    library_id: Annotated[
        str | None,
        Field(
            alias="libraryId",
            description="Identifies the library associated with this risk range.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="Identifies the engagement associated with this risk range.",
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(
            alias="analysisTypeId",
            description="Identifies the analysis type associated with this risk range.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the risk range.", max_length=80, min_length=0),
    ] = None
    description: Annotated[
        str | None,
        Field(
            description="The description of the risk range.",
            max_length=250,
            min_length=0,
        ),
    ] = None


class ApiOrganizationUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the organization.", max_length=80, min_length=0),
    ] = None
    external_client_code: Annotated[
        str | None,
        Field(
            alias="externalClientCode",
            description="The unique client ID applied to this organization.",
            max_length=80,
            min_length=0,
        ),
    ] = None
    manager_user_ids: Annotated[
        list[str] | None,
        Field(
            alias="managerUserIds",
            description="Identifies users assigned to the organization manager role.",
        ),
    ] = None


class ApiOrganizationRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the organization.", max_length=80, min_length=0),
    ] = None
    external_client_code: Annotated[
        str | None,
        Field(
            alias="externalClientCode",
            description="The unique client ID applied to this organization.",
            max_length=80,
            min_length=0,
        ),
    ] = None
    manager_user_ids: Annotated[
        list[str] | None,
        Field(
            alias="managerUserIds",
            description="Identifies users assigned to the organization manager role.",
        ),
    ] = None


class ApiLibraryUpdateRiskScoreDisplay(str, Enum):
    """Determines whether risk scores will be presented as percentages (%), or using High, Medium, and Low label indicators."""

    HIGH_MEDIUM_LOW = "HIGH_MEDIUM_LOW"
    PERCENTAGE = "PERCENTAGE"


class ApiLibraryUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(
            description="The current name of the library.", max_length=80, min_length=0
        ),
    ] = None
    warnings_dismissed: Annotated[
        bool | None,
        Field(
            alias="warningsDismissed",
            description="When set to `true`, any conversion warnings for this library will not be displayed in the **Libraries** tab in the UI.",
        ),
    ] = None
    analysis_type_ids: Annotated[
        list[str] | None,
        Field(
            alias="analysisTypeIds",
            description="Identifies the analysis types used in the library.",
        ),
    ] = None
    default_delimiter: Annotated[
        str | None,
        Field(
            alias="defaultDelimiter",
            description="Identifies the default delimiter used in imported CSV files.",
        ),
    ] = None
    control_point_selection_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointSelectionPermission",
            description="When set to `true`, control points can be added or removed within each risk score.",
        ),
    ] = None
    control_point_weight_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointWeightPermission",
            description="When set to `true`, the weight of each control point can be adjusted within each risk score.",
        ),
    ] = None
    control_point_settings_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointSettingsPermission",
            description="When set to `true`, individual control point settings can be adjusted within each risk score.",
        ),
    ] = None
    risk_score_and_groups_selection_permission: Annotated[
        bool | None,
        Field(
            alias="riskScoreAndGroupsSelectionPermission",
            description="When set to `true`, risk scores and groups can be disabled, and accounts associated with risk scores can be edited.",
        ),
    ] = None
    risk_range_edit_permission: Annotated[
        bool | None, Field(alias="riskRangeEditPermission")
    ] = None
    risk_score_display: Annotated[
        ApiLibraryUpdateRiskScoreDisplay | None,
        Field(
            alias="riskScoreDisplay",
            description="Determines whether risk scores will be presented as percentages (%), or using High, Medium, and Low label indicators.",
        ),
    ] = None
    archived: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the library is archived. Archived libraries cannot be selected when creating an engagement."
        ),
    ] = None


class ApiLibraryReadRiskScoreDisplay(str, Enum):
    """Determines whether risk scores will be presented as percentages (%), or using High, Medium, and Low label indicators."""

    HIGH_MEDIUM_LOW = "HIGH_MEDIUM_LOW"
    PERCENTAGE = "PERCENTAGE"


class ProblemReadProblemType(str, Enum):
    """The type of problem."""

    UNKNOWN = "UNKNOWN"
    ILLEGAL_ARGUMENT = "ILLEGAL_ARGUMENT"
    CANNOT_DELETE = "CANNOT_DELETE"
    GREATER_VALUE_REQUIRED = "GREATER_VALUE_REQUIRED"
    LESS_VALUE_REQUIRED = "LESS_VALUE_REQUIRED"
    NON_UNIQUE_VALUE = "NON_UNIQUE_VALUE"
    USER_EMAIL_ALREADY_EXISTS = "USER_EMAIL_ALREADY_EXISTS"
    INCORRECT_DATA_TYPE = "INCORRECT_DATA_TYPE"
    RATIO_CONVERSION_FAILED = "RATIO_CONVERSION_FAILED"
    RISK_SCORE_FILTER_CONVERSION_FAILED = "RISK_SCORE_FILTER_CONVERSION_FAILED"
    FILTER_CONVERSION_FAILED = "FILTER_CONVERSION_FAILED"
    POPULATION_CONVERSION_FAILED = "POPULATION_CONVERSION_FAILED"
    INSUFFICIENT_PERMISSION = "INSUFFICIENT_PERMISSION"
    ACCOUNT_GROUPING_NODES_CONTAIN_ERRORS = "ACCOUNT_GROUPING_NODES_CONTAIN_ERRORS"
    ACCOUNT_GROUPING_IN_USE_BY_LIBRARY = "ACCOUNT_GROUPING_IN_USE_BY_LIBRARY"
    INVALID_ACCOUNT_GROUPING_FILE = "INVALID_ACCOUNT_GROUPING_FILE"
    DELIVERY_FAILURE = "DELIVERY_FAILURE"
    INVALID_STATE = "INVALID_STATE"


class ProblemReadSeverity(str, Enum):
    """Indicates how severe the problem is."""

    WARNING = "WARNING"
    ERROR = "ERROR"


class ProblemRead(BaseItem):
    problem_type: Annotated[
        ProblemReadProblemType | None,
        Field(alias="problemType", description="The type of problem."),
    ] = None
    severity: Annotated[
        ProblemReadSeverity | None,
        Field(description="Indicates how severe the problem is."),
    ] = None
    entity_type: Annotated[
        str | None,
        Field(
            alias="entityType",
            description="The type of entity impacted by the problem.",
        ),
    ] = None
    entity_id: Annotated[
        str | None,
        Field(
            alias="entityId",
            description="Identifies the entity impacted by the problem.",
        ),
    ] = None
    identifier: Annotated[
        str | None, Field(description="Identifies the field causing the problem.")
    ] = None
    values: Annotated[
        list[str] | None,
        Field(description="Identifies the values causing the problem."),
    ] = None
    reason: Annotated[
        str | None, Field(description="The reason(s) why the problem occurred.")
    ] = None
    suggested_values: Annotated[
        list[str] | None,
        Field(
            alias="suggestedValues",
            description="A suggested set of values to assist in resolving the problem.",
        ),
    ] = None
    problem_count: Annotated[
        int | None,
        Field(
            alias="problemCount",
            description="The total number of occurrences of this problem.",
        ),
    ] = None


class ApiFileManagerEntityUpdateType(str, Enum):
    """Indicates whether the object is a DIRECTORY or a FILE."""

    DIRECTORY = "DIRECTORY"
    FILE = "FILE"


class ApiFileManagerEntityUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    type: Annotated[
        ApiFileManagerEntityUpdateType | None,
        Field(description="Indicates whether the object is a DIRECTORY or a FILE."),
    ] = None
    parent_file_manager_entity_id: Annotated[
        str | None,
        Field(
            alias="parentFileManagerEntityId",
            description="Identifies the parent directory. If NULL, the directory is positioned at the root level.",
        ),
    ] = None


class ApiFileManagerFileUpdate(ApiFileManagerEntityUpdate):
    name: Annotated[
        str | None,
        Field(description="The current name of the file, excluding the extension."),
    ] = None
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiFileManagerEntityReadType(str, Enum):
    """Indicates whether the object is a DIRECTORY or a FILE."""

    DIRECTORY = "DIRECTORY"
    FILE = "FILE"


class ApiFileManagerEntityRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    type: Annotated[
        ApiFileManagerEntityReadType | None,
        Field(description="Indicates whether the object is a DIRECTORY or a FILE."),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    parent_file_manager_entity_id: Annotated[
        str | None,
        Field(
            alias="parentFileManagerEntityId",
            description="Identifies the parent directory. If NULL, the directory is positioned at the root level.",
        ),
    ] = None


class StatusEnum(str, Enum):
    MODIFIED = "MODIFIED"
    ROLLED_FORWARD = "ROLLED_FORWARD"


class ApiFileManagerFileRead(ApiFileManagerEntityRead):
    original_name: Annotated[
        str | None,
        Field(
            alias="originalName",
            description="The name of the file as it appeared when first imported, including the extension.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The current name of the file, excluding the extension."),
    ] = None
    extension: Annotated[
        str | None, Field(description="The suffix used at the end of the file.")
    ] = None
    status: Annotated[
        list[StatusEnum] | None,
        Field(description="The status of the file as it appears in MindBridge."),
    ] = None
    file_info_id: Annotated[
        str | None,
        Field(alias="fileInfoId", description="Identifies the associated file info."),
    ] = None
    engagement_id: Annotated[
        str,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiAccountingPeriodUpdateFrequency(str, Enum):
    """The frequency with which your client's financial data is reported."""

    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    THIRTEEN_PERIODS = "THIRTEEN_PERIODS"


class ApiAccountingPeriodUpdate(BaseItem):
    fiscal_start_month: Annotated[
        int | None,
        Field(
            alias="fiscalStartMonth",
            description="The month that the fiscal period begins.",
        ),
    ] = None
    fiscal_start_day: Annotated[
        int | None,
        Field(
            alias="fiscalStartDay",
            description="The date of the month that the fiscal period begins.",
        ),
    ] = None
    frequency: Annotated[
        ApiAccountingPeriodUpdateFrequency | None,
        Field(
            description="The frequency with which your client's financial data is reported."
        ),
    ] = None


class ApiEngagementUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the engagement.", max_length=80, min_length=0),
    ] = None
    billing_code: Annotated[
        str | None,
        Field(
            alias="billingCode",
            description="A unique code that associates engagements and analyses with clients to ensure those clients are billed appropriately for MindBridge usage.",
        ),
    ] = None
    accounting_period: Annotated[
        ApiAccountingPeriodUpdate | None,
        Field(
            alias="accountingPeriod", description="Details about the accounting period."
        ),
    ] = None
    audit_period_end_date: Annotated[
        date | None,
        Field(
            alias="auditPeriodEndDate",
            description="The last day of the occurring audit.",
        ),
    ] = None
    accounting_package: Annotated[
        str | None,
        Field(
            alias="accountingPackage",
            description="The ERP or financial management system that your client is using.",
        ),
    ] = None
    industry: Annotated[
        str | None,
        Field(description="The type of industry that your client operates within."),
    ] = None
    engagement_lead_id: Annotated[
        str | None,
        Field(
            alias="engagementLeadId",
            description="Identifies the user who will lead the engagement.",
        ),
    ] = None
    reporting_period_configuration_id: Annotated[
        str | None,
        Field(
            alias="reportingPeriodConfigurationId",
            description="Identifies the associated reporting period configuration. If null the analyses use a standard reporting period.",
        ),
    ] = None
    auditor_ids: Annotated[
        list[str] | None,
        Field(
            alias="auditorIds",
            description="Identifies the users who will act as auditors in the engagement.",
        ),
    ] = None


class ApiAccountingPeriodReadFrequency(str, Enum):
    """The frequency with which your client's financial data is reported."""

    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    THIRTEEN_PERIODS = "THIRTEEN_PERIODS"


class ApiAccountingPeriodRead(BaseItem):
    fiscal_start_month: Annotated[
        int | None,
        Field(
            alias="fiscalStartMonth",
            description="The month that the fiscal period begins.",
        ),
    ] = None
    fiscal_start_day: Annotated[
        int | None,
        Field(
            alias="fiscalStartDay",
            description="The date of the month that the fiscal period begins.",
        ),
    ] = None
    frequency: Annotated[
        ApiAccountingPeriodReadFrequency | None,
        Field(
            description="The frequency with which your client's financial data is reported."
        ),
    ] = None


class ApiEngagementRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    organization_id: Annotated[
        str | None,
        Field(alias="organizationId", description="Identifies the organization."),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the engagement.", max_length=80, min_length=0),
    ] = None
    billing_code: Annotated[
        str | None,
        Field(
            alias="billingCode",
            description="A unique code that associates engagements and analyses with clients to ensure those clients are billed appropriately for MindBridge usage.",
        ),
    ] = None
    library_id: Annotated[
        str | None, Field(alias="libraryId", description="Identifies the library.")
    ] = None
    accounting_period: Annotated[
        ApiAccountingPeriodRead | None,
        Field(
            alias="accountingPeriod", description="Details about the accounting period."
        ),
    ] = None
    audit_period_end_date: Annotated[
        date | None,
        Field(
            alias="auditPeriodEndDate",
            description="The last day of the occurring audit.",
        ),
    ] = None
    accounting_package: Annotated[
        str | None,
        Field(
            alias="accountingPackage",
            description="The ERP or financial management system that your client is using.",
        ),
    ] = None
    industry: Annotated[
        str | None,
        Field(description="The type of industry that your client operates within."),
    ] = None
    engagement_lead_id: Annotated[
        str | None,
        Field(
            alias="engagementLeadId",
            description="Identifies the user who will lead the engagement.",
        ),
    ] = None
    reporting_period_configuration_id: Annotated[
        str | None,
        Field(
            alias="reportingPeriodConfigurationId",
            description="Identifies the associated reporting period configuration. If null the analyses use a standard reporting period.",
        ),
    ] = None
    auditor_ids: Annotated[
        list[str] | None,
        Field(
            alias="auditorIds",
            description="Identifies the users who will act as auditors in the engagement.",
        ),
    ] = None


class ApiEngagementAccountGroupUpdate(BaseItem):
    code: Annotated[
        str | None, Field(description="The account code for this account group.")
    ] = None
    mac_code: Annotated[
        str | None,
        Field(
            alias="macCode", description="The MAC code mapped to this account group."
        ),
    ] = None
    hidden: Annotated[
        bool | None,
        Field(
            description="When `true` this account is hidden, and can't be used in account mapping. Additionally this account won't be suggested when automatically mapping accounts during file import."
        ),
    ] = None
    alias: Annotated[
        str | None,
        Field(
            description="A replacement value used when displaying the account description.\n\nThis does not have any effect on automatic column mapping."
        ),
    ] = None


class ApiAccountGroupErrorReadType(str, Enum):
    """The type of account group error."""

    ERROR_LOWEST_LEVEL_WITH_NO_MAC = "ERROR_LOWEST_LEVEL_WITH_NO_MAC"
    ERROR_LOWEST_LEVEL_WITHOUT_LEVEL_4_MAC = "ERROR_LOWEST_LEVEL_WITHOUT_LEVEL_4_MAC"
    ERROR_INCONSISTENT_SHEET_HIERARCHY = "ERROR_INCONSISTENT_SHEET_HIERARCHY"


class ApiAccountGroupErrorRead(BaseItem):
    type: Annotated[
        ApiAccountGroupErrorReadType | None,
        Field(description="The type of account group error."),
    ] = None
    arguments: Annotated[
        list[str] | None,
        Field(
            description="A list of values relevant to the type of account group error."
        ),
    ] = None


class ApiEngagementAccountGroupReadOrigin(str, Enum):
    """The process that lead to the creation of the account group."""

    IMPORTED_FROM_LIBRARY = "IMPORTED_FROM_LIBRARY"
    IMPORTED_FROM_ENGAGEMENT = "IMPORTED_FROM_ENGAGEMENT"
    ADDED_ON_ENGAGEMENT = "ADDED_ON_ENGAGEMENT"


class ApiEngagementAccountGroupRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    engagement_account_grouping_id: Annotated[
        str | None,
        Field(
            alias="engagementAccountGroupingId",
            description="The unique identifier for the engagement account grouping that the engagement account group belongs to.",
        ),
    ] = None
    code: Annotated[
        str | None, Field(description="The account code for this account group.")
    ] = None
    description: Annotated[
        dict[str, str] | None,
        Field(description="A description of the account code for this account group."),
    ] = None
    lowest_level: Annotated[bool | None, Field(alias="lowestLevel")] = None
    hierarchy: Annotated[
        list[str] | None,
        Field(description="A list of the parent codes for this account group."),
    ] = None
    parent_code: Annotated[
        str | None,
        Field(
            alias="parentCode", description="The parent code for this account group."
        ),
    ] = None
    mac_code: Annotated[
        str | None,
        Field(
            alias="macCode", description="The MAC code mapped to this account group."
        ),
    ] = None
    account_tags: Annotated[
        list[str] | None,
        Field(
            alias="accountTags",
            description="A list of account tags assigned to this account group.",
        ),
    ] = None
    published_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="publishedDate",
            description="The date this account group was published. If not set, this account group is not published.\n\nPublished account groups cannot be updated.",
        ),
    ] = None
    order_index: Annotated[
        int | None,
        Field(
            alias="orderIndex",
            description="The order in which this account group is displayed, relative to other account groups with the same parent.",
        ),
    ] = None
    errors: Annotated[
        list[ApiAccountGroupErrorRead] | None,
        Field(description="A list of errors associated with this account group."),
    ] = None
    hidden: Annotated[
        bool | None,
        Field(
            description="When `true` this account is hidden, and can't be used in account mapping. Additionally this account won't be suggested when automatically mapping accounts during file import."
        ),
    ] = None
    origin: Annotated[
        ApiEngagementAccountGroupReadOrigin | None,
        Field(
            description="The process that lead to the creation of the account group."
        ),
    ] = None
    alias: Annotated[
        str | None,
        Field(
            description="A replacement value used when displaying the account description.\n\nThis does not have any effect on automatic column mapping."
        ),
    ] = None


class ApiDatabricksAuthorizationUpdateAuthType(str, Enum):
    """The authentication method to use. Possible values: PAT, OAUTH_M2M."""

    PAT = "PAT"
    OAUTH_M2_M = "OAUTH_M2M"


class ApiDatabricksAuthorizationUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection this authorization belongs to.",
        ),
    ] = None
    auth_type: Annotated[
        ApiDatabricksAuthorizationUpdateAuthType | None,
        Field(
            alias="authType",
            description="The authentication method to use. Possible values: PAT, OAUTH_M2M.",
        ),
    ] = None
    host: Annotated[
        str | None, Field(description="The Databricks server hostname.")
    ] = None
    port: Annotated[
        int | None,
        Field(
            description="The port number for the Databricks connection. Typically 443."
        ),
    ] = None
    http_path: Annotated[
        str | None,
        Field(
            alias="httpPath",
            description="The HTTP path for the Databricks SQL warehouse or cluster.",
        ),
    ] = None
    access_token: Annotated[
        str | None,
        Field(
            alias="accessToken",
            description="The personal access token for PAT authentication.",
        ),
    ] = None
    client_id: Annotated[
        str | None,
        Field(
            alias="clientId",
            description="The OAuth client ID for OAUTH_M2M authentication.",
        ),
    ] = None
    client_secret: Annotated[
        str | None,
        Field(
            alias="clientSecret",
            description="The OAuth client secret for OAUTH_M2M authentication.",
        ),
    ] = None


class ApiDatabricksAuthorizationReadAuthType(str, Enum):
    """The authentication method to use. Possible values: PAT, OAUTH_M2M."""

    PAT = "PAT"
    OAUTH_M2_M = "OAUTH_M2M"


class ApiDatabricksAuthorizationRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection this authorization belongs to.",
        ),
    ] = None
    auth_type: Annotated[
        ApiDatabricksAuthorizationReadAuthType | None,
        Field(
            alias="authType",
            description="The authentication method to use. Possible values: PAT, OAUTH_M2M.",
        ),
    ] = None
    host: Annotated[
        str | None, Field(description="The Databricks server hostname.")
    ] = None
    port: Annotated[
        int | None,
        Field(
            description="The port number for the Databricks connection. Typically 443."
        ),
    ] = None
    http_path: Annotated[
        str | None,
        Field(
            alias="httpPath",
            description="The HTTP path for the Databricks SQL warehouse or cluster.",
        ),
    ] = None
    client_id: Annotated[
        str | None,
        Field(
            alias="clientId",
            description="The OAuth client ID for OAUTH_M2M authentication.",
        ),
    ] = None


class ApiApiTokenUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(
            description="The token record's name. This will also be used as the API Token User's name."
        ),
    ] = None


class ApiApiTokenReadPermission(str, Enum):
    API_ORGANIZATIONS_READ = "api.organizations.read"
    API_ORGANIZATIONS_WRITE = "api.organizations.write"
    API_ORGANIZATIONS_DELETE = "api.organizations.delete"
    API_ENGAGEMENTS_READ = "api.engagements.read"
    API_ENGAGEMENTS_WRITE = "api.engagements.write"
    API_ENGAGEMENTS_DELETE = "api.engagements.delete"
    API_ANALYSES_READ = "api.analyses.read"
    API_ANALYSES_WRITE = "api.analyses.write"
    API_ANALYSES_DELETE = "api.analyses.delete"
    API_ANALYSES_RUN = "api.analyses.run"
    API_ANALYSIS_SOURCES_READ = "api.analysis-sources.read"
    API_ANALYSIS_SOURCES_WRITE = "api.analysis-sources.write"
    API_ANALYSIS_SOURCES_DELETE = "api.analysis-sources.delete"
    API_FILE_MANAGER_READ = "api.file-manager.read"
    API_FILE_MANAGER_WRITE = "api.file-manager.write"
    API_FILE_MANAGER_DELETE = "api.file-manager.delete"
    API_REPORTING_PERIOD_CONFIG_READ = "api.reporting-period-config.read"
    API_REPORTING_PERIOD_CONFIG_WRITE = "api.reporting-period-config.write"
    API_REPORTING_PERIOD_CONFIG_DELETE = "api.reporting-period-config.delete"
    API_LIBRARIES_READ = "api.libraries.read"
    API_LIBRARIES_WRITE = "api.libraries.write"
    API_LIBRARIES_DELETE = "api.libraries.delete"
    API_ACCOUNT_GROUPINGS_READ = "api.account-groupings.read"
    API_ACCOUNT_GROUPINGS_WRITE = "api.account-groupings.write"
    API_ACCOUNT_GROUPINGS_DELETE = "api.account-groupings.delete"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_READ = "api.engagement-account-groupings.read"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_WRITE = "api.engagement-account-groupings.write"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_DELETE = "api.engagement-account-groupings.delete"
    API_USERS_READ = "api.users.read"
    API_USERS_WRITE = "api.users.write"
    API_USERS_DELETE = "api.users.delete"
    API_DATA_TABLES_READ = "api.data-tables.read"
    API_API_TOKENS_READ = "api.api-tokens.read"
    API_API_TOKENS_WRITE = "api.api-tokens.write"
    API_API_TOKENS_DELETE = "api.api-tokens.delete"
    API_TASKS_READ = "api.tasks.read"
    API_TASKS_WRITE = "api.tasks.write"
    API_TASKS_DELETE = "api.tasks.delete"
    API_ADMIN_REPORTS_RUN = "api.admin-reports.run"
    API_ANALYSIS_TYPES_READ = "api.analysis-types.read"
    API_ANALYSIS_SOURCE_TYPES_READ = "api.analysis-source-types.read"
    API_ANALYSIS_TYPE_CONFIGURATION_READ = "api.analysis-type-configuration.read"
    API_ANALYSIS_TYPE_CONFIGURATION_WRITE = "api.analysis-type-configuration.write"
    API_ANALYSIS_TYPE_CONFIGURATION_DELETE = "api.analysis-type-configuration.delete"
    API_RISK_RANGES_READ = "api.risk-ranges.read"
    API_RISK_RANGES_WRITE = "api.risk-ranges.write"
    API_RISK_RANGES_DELETE = "api.risk-ranges.delete"
    API_FILTERS_READ = "api.filters.read"
    API_FILTERS_WRITE = "api.filters.write"
    API_FILTERS_DELETE = "api.filters.delete"
    API_FILE_INFOS_READ = "api.file-infos.read"
    API_WEBHOOKS_READ = "api.webhooks.read"
    API_WEBHOOKS_WRITE = "api.webhooks.write"
    API_WEBHOOKS_DELETE = "api.webhooks.delete"
    API_CONNECTIONS_READ = "api.connections.read"
    API_CONNECTIONS_WRITE = "api.connections.write"
    API_CONNECTIONS_DELETE = "api.connections.delete"
    API_CONNECTION_DATA_SOURCES_READ = "api.connection-data-sources.read"
    API_CONNECTION_DATA_SOURCES_WRITE = "api.connection-data-sources.write"
    API_CONNECTION_DATA_SOURCES_DELETE = "api.connection-data-sources.delete"
    SCIM_USER_READ = "scim.user.read"
    SCIM_USER_WRITE = "scim.user.write"
    SCIM_USER_DELETE = "scim.user.delete"
    SCIM_USER_SCHEMA = "scim.user.schema"


class ApiApiTokenRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    user_id: Annotated[
        str | None,
        Field(
            alias="userId",
            description="Identifies the API Token User associated with this token.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(
            description="The token record's name. This will also be used as the API Token User's name."
        ),
    ] = None
    partial_token: Annotated[
        str | None,
        Field(
            alias="partialToken",
            description="A partial representation of the API token.",
        ),
    ] = None
    expiry: Annotated[
        AwareDatetime | None,
        Field(description="The day on which the API token expires."),
    ] = None
    allowed_addresses: Annotated[
        list[str] | None,
        Field(
            alias="allowedAddresses",
            description="Indicates the set of addresses that are allowed to use this token. If empty, any address may use it.",
        ),
    ] = None
    permissions: Annotated[
        list[ApiApiTokenReadPermission] | None,
        Field(
            description="The set of permissions that inform which endpoints this token is authorized to access."
        ),
    ] = None


class ApiRiskGroupFilterUpdate(BaseItem):
    values: Annotated[
        list[str] | None,
        Field(description="A list of accounts to include in the risk group."),
    ] = None


class ApiRiskGroupUpdate(BaseItem):
    disabled: Annotated[
        bool | None, Field(description="Indicates whether the risk group is disabled.")
    ] = None
    id: Annotated[
        str | None,
        Field(description="The unique object identifier for this risk group."),
    ] = None
    selected_risk_range: Annotated[
        str | None,
        Field(
            alias="selectedRiskRange",
            description="The selected risk range for the risk group. The selected value must be part of the applicable risk ranges.",
        ),
    ] = None
    applicable_risk_ranges: Annotated[
        list[str] | None,
        Field(
            alias="applicableRiskRanges",
            description="A list of risk ranges that are applicable to the risk group.",
        ),
    ] = None
    filter: Annotated[
        ApiRiskGroupFilterUpdate | None,
        Field(
            description="A filter based on account hierarchy used to determine which entries are included in the risk group."
        ),
    ] = None
    control_point_weights: Annotated[
        dict[str, int] | None,
        Field(
            alias="controlPointWeights",
            description="A map of control point names to their weights within the risk group.",
        ),
    ] = None


class ApiRiskGroupFilterRead(BaseItem):
    values: Annotated[
        list[str] | None,
        Field(description="A list of accounts to include in the risk group."),
    ] = None


class ApiRiskGroupReadRiskAssertionCategory(str, Enum):
    """Identifies the risk assertion category of the risk group."""

    GENERAL = "GENERAL"
    ASSETS = "ASSETS"
    LIABILITIES_EQUITY = "LIABILITIES_EQUITY"
    PROFIT_LOSS = "PROFIT_LOSS"
    LIABILITIES = "LIABILITIES"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSES = "EXPENSES"


class ApiRiskGroupRead(BaseItem):
    disabled: Annotated[
        bool | None, Field(description="Indicates whether the risk group is disabled.")
    ] = None
    id: Annotated[
        str | None,
        Field(description="The unique object identifier for this risk group."),
    ] = None
    system: Annotated[
        bool | None,
        Field(
            description="Indicates whether the risk group is a MindBridge system risk group."
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(
            alias="analysisTypeId",
            description="Identifies the analysis type that the risk group is associated with.",
        ),
    ] = None
    selected_risk_range: Annotated[
        str | None,
        Field(
            alias="selectedRiskRange",
            description="The selected risk range for the risk group. The selected value must be part of the applicable risk ranges.",
        ),
    ] = None
    applicable_risk_ranges: Annotated[
        list[str] | None,
        Field(
            alias="applicableRiskRanges",
            description="A list of risk ranges that are applicable to the risk group.",
        ),
    ] = None
    filter: Annotated[
        ApiRiskGroupFilterRead | None,
        Field(
            description="A filter based on account hierarchy used to determine which entries are included in the risk group."
        ),
    ] = None
    control_point_weights: Annotated[
        dict[str, int] | None,
        Field(
            alias="controlPointWeights",
            description="A map of control point names to their weights within the risk group.",
        ),
    ] = None
    control_point_bundle_version: Annotated[
        str | None,
        Field(
            alias="controlPointBundleVersion",
            description="The version of the control point bundle used in this risk group.",
        ),
    ] = None
    name: Annotated[
        dict[str, str] | None,
        Field(
            description="A map of localized risk group names, keyed by language code."
        ),
    ] = None
    description: Annotated[
        dict[str, str] | None,
        Field(
            description="A map of localized risk group descriptions, keyed by language code."
        ),
    ] = None
    category: Annotated[
        dict[str, str] | None,
        Field(description="Identifies the risk group's category."),
    ] = None
    risk_assertion_category: Annotated[
        ApiRiskGroupReadRiskAssertionCategory | None,
        Field(
            alias="riskAssertionCategory",
            description="Identifies the risk assertion category of the risk group.",
        ),
    ] = None


class ApiAmbiguousColumnUpdate(BaseItem):
    position: Annotated[
        int | None, Field(description="The position of the column with the resolution.")
    ] = None
    selected_format: Annotated[
        str | None,
        Field(
            alias="selectedFormat",
            description="The data format to be used in case of ambiguity.",
        ),
    ] = None


class ApiAnalysisSourceUpdateTargetWorkflowState(str, Enum):
    """The state that the current workflow will advance to."""

    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    STARTED = "STARTED"
    DETECTING_FORMAT = "DETECTING_FORMAT"
    ANALYZING_COLUMNS = "ANALYZING_COLUMNS"
    CHECKING_INTEGRITY = "CHECKING_INTEGRITY"
    SCANNING_TRANSACTION_COMBINATIONS = "SCANNING_TRANSACTION_COMBINATIONS"
    PARSING = "PARSING"
    PARSING_ICEBERG = "PARSING_ICEBERG"
    ANALYZING_EFFECTIVE_DATE_METRICS = "ANALYZING_EFFECTIVE_DATE_METRICS"
    FORMAT_DETECTION_COMPLETED = "FORMAT_DETECTION_COMPLETED"
    COLUMN_MAPPINGS_CONFIRMED = "COLUMN_MAPPINGS_CONFIRMED"
    SETTINGS_CONFIRMED = "SETTINGS_CONFIRMED"
    PREPARING_ICEBERG = "PREPARING_ICEBERG"
    ANALYSIS_PERIOD_SELECTED = "ANALYSIS_PERIOD_SELECTED"
    FUNDS_REVIEWED = "FUNDS_REVIEWED"
    RUNNING = "RUNNING"
    UNPACK_COMPLETE = "UNPACK_COMPLETE"
    UPLOADED = "UPLOADED"
    FORMAT_DETECTED = "FORMAT_DETECTED"
    COLUMNS_ANALYZED = "COLUMNS_ANALYZED"
    INTEGRITY_CHECKED = "INTEGRITY_CHECKED"
    PARSED = "PARSED"
    AUTHENTICATED = "AUTHENTICATED"
    CONFIGURED = "CONFIGURED"
    EFFECTIVE_DATE_METRICS_ANALYZED = "EFFECTIVE_DATE_METRICS_ANALYZED"
    DATA_VALIDATION_CONFIRMED = "DATA_VALIDATION_CONFIRMED"


class ApiColumnMappingUpdate(BaseItem):
    position: Annotated[
        int | None, Field(description="The position of the column mapping.")
    ] = None
    mindbridge_field: Annotated[
        str | None,
        Field(
            alias="mindbridgeField",
            description="The MindBridge field that the data column was mapped to.",
        ),
    ] = None
    additional_column_name: Annotated[
        str | None,
        Field(
            alias="additionalColumnName",
            description="Additional columns of data that were added to the analysis.",
        ),
    ] = None


class ApiProposedAmbiguousColumnResolutionUpdate(BaseItem):
    position: Annotated[
        int | None,
        Field(
            description="The position of the column with the proposed resolution.", ge=0
        ),
    ] = None
    selected_format: Annotated[
        str | None,
        Field(
            alias="selectedFormat",
            description="The selected format of the proposed resolution.",
        ),
    ] = None


class ApiProposedColumnMappingUpdate(BaseItem):
    column_position: Annotated[
        int | None,
        Field(
            alias="columnPosition",
            description="The position of the proposed column mapping in the original input file.",
        ),
    ] = None
    virtual_column_index: Annotated[
        int | None,
        Field(
            alias="virtualColumnIndex",
            description="The position of the proposed virtual columns within the `proposedVirtualColumns` list.",
        ),
    ] = None
    mindbridge_field: Annotated[
        str | None,
        Field(
            alias="mindbridgeField",
            description="The MindBridge field that the data column should be mapped to.",
        ),
    ] = None
    additional_column_name: Annotated[
        str | None,
        Field(
            alias="additionalColumnName",
            description="Proposed additional columns of data to be added to the analysis.",
        ),
    ] = None


class ApiProposedVirtualColumnUpdateType(str, Enum):
    """The type of proposed virtual column."""

    DUPLICATE = "DUPLICATE"
    SPLIT_BY_POSITION = "SPLIT_BY_POSITION"
    SPLIT_BY_DELIMITER = "SPLIT_BY_DELIMITER"
    JOIN = "JOIN"


class ApiProposedVirtualColumnUpdate(BaseItem):
    name: Annotated[
        str | None, Field(description="The name of the proposed virtual column.")
    ] = None
    type: Annotated[
        ApiProposedVirtualColumnUpdateType | None,
        Field(description="The type of proposed virtual column."),
    ] = None


class ApiTransactionIdSelectionUpdateType(str, Enum):
    """The type used when selecting a transaction ID."""

    COMBINATION = "COMBINATION"
    RUNNING_TOTAL = "RUNNING_TOTAL"


class ApiTransactionIdSelectionUpdate(BaseItem):
    column_selection: Annotated[
        list[int] | None,
        Field(
            alias="columnSelection",
            description="The columns included when selecting a transaction ID.",
        ),
    ] = None
    virtual_column_selection: Annotated[
        list[int] | None,
        Field(
            alias="virtualColumnSelection",
            description="The virtual columns included when selecting a transaction ID.",
        ),
    ] = None
    type: Annotated[
        ApiTransactionIdSelectionUpdateType | None,
        Field(description="The type used when selecting a transaction ID."),
    ] = None
    apply_smart_splitter: Annotated[
        bool | None,
        Field(
            alias="applySmartSplitter",
            description="Indicates whether or not the Smart Splitter was run when selecting a transaction ID.",
        ),
    ] = None


class ApiVirtualColumnUpdateType(str, Enum):
    """The type of virtual column."""

    DUPLICATE = "DUPLICATE"
    SPLIT_BY_POSITION = "SPLIT_BY_POSITION"
    SPLIT_BY_DELIMITER = "SPLIT_BY_DELIMITER"
    JOIN = "JOIN"


class ApiVirtualColumnUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    name: Annotated[
        str | None, Field(description="The name of the virtual column.")
    ] = None
    type: Annotated[
        ApiVirtualColumnUpdateType | None,
        Field(description="The type of virtual column."),
    ] = None


class ApiAsyncResultReadType(str, Enum):
    """Indicates the type of job being run."""

    ANALYSIS_RUN = "ANALYSIS_RUN"
    ANALYSIS_SOURCE_INGESTION = "ANALYSIS_SOURCE_INGESTION"
    ADMIN_REPORT = "ADMIN_REPORT"
    DATA_TABLE_EXPORT = "DATA_TABLE_EXPORT"
    ANALYSIS_ROLL_FORWARD = "ANALYSIS_ROLL_FORWARD"
    GDPDU_UNPACK_JOB = "GDPDU_UNPACK_JOB"
    ACCOUNT_GROUPING_EXPORT = "ACCOUNT_GROUPING_EXPORT"
    ACCOUNT_MAPPING_EXPORT = "ACCOUNT_MAPPING_EXPORT"
    DATA_TRANSFORMATION_JOB = "DATA_TRANSFORMATION_JOB"
    CONNECTION_TEST = "CONNECTION_TEST"
    CONNECTION_TABLES = "CONNECTION_TABLES"
    DATA_TABLE = "DATA_TABLE"


class ApiAsyncResultReadStatus(str, Enum):
    """Indicates the current state of the job."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class ApiAsyncResultReadEntityType(str, Enum):
    """Identifies the entity type used in the job."""

    ORGANIZATION = "ORGANIZATION"
    ENGAGEMENT = "ENGAGEMENT"
    ANALYSIS = "ANALYSIS"
    ANALYSIS_RESULT = "ANALYSIS_RESULT"
    ANALYSIS_SOURCE = "ANALYSIS_SOURCE"
    FILE_RESULT = "FILE_RESULT"
    GDPDU_UNPACK_JOB = "GDPDU_UNPACK_JOB"
    ACCOUNT_GROUPING = "ACCOUNT_GROUPING"
    ENGAGEMENT_ACCOUNT_GROUPING = "ENGAGEMENT_ACCOUNT_GROUPING"
    FILE_MANAGER_FILE = "FILE_MANAGER_FILE"
    CONNECTION_TEST_RESULT = "CONNECTION_TEST_RESULT"
    CONNECTION_TABLES_RESULT = "CONNECTION_TABLES_RESULT"
    DATA_TABLE = "DATA_TABLE"


class ApiAsyncResultRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    type: Annotated[
        ApiAsyncResultReadType | None,
        Field(description="Indicates the type of job being run."),
    ] = None
    status: Annotated[
        ApiAsyncResultReadStatus | None,
        Field(description="Indicates the current state of the job."),
    ] = None
    entity_id: Annotated[
        str | None,
        Field(alias="entityId", description="Identifies the entity used in the job."),
    ] = None
    entity_type: Annotated[
        ApiAsyncResultReadEntityType | None,
        Field(
            alias="entityType",
            description="Identifies the entity type used in the job.",
        ),
    ] = None
    error: Annotated[
        str | None, Field(description="The reason why the async job failed.")
    ] = None
    error_message: Annotated[str | None, Field(alias="errorMessage")] = None


class ApiAnalysisPeriodUpdate(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    start_date: Annotated[
        date | None,
        Field(
            alias="startDate", description="The first day of the period under analysis."
        ),
    ] = None
    interim_as_at_date: Annotated[
        date | None,
        Field(
            alias="interimAsAtDate",
            description="The last day of the interim period under analysis.",
        ),
    ] = None
    end_date: Annotated[
        date | None,
        Field(
            alias="endDate", description="The last day of the period under analysis."
        ),
    ] = None


class ApiAnalysisUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the analysis.", max_length=80, min_length=0),
    ] = None
    archived: Annotated[
        bool | None,
        Field(description="Indicates whether or not the analysis has been archived."),
    ] = None
    analysis_periods: Annotated[
        list[ApiAnalysisPeriodUpdate] | None,
        Field(
            alias="analysisPeriods",
            description="Details about the specific analysis periods under audit.",
        ),
    ] = None
    currency_code: Annotated[
        str | None,
        Field(
            alias="currencyCode",
            description="The currency to be displayed across the analysis results.",
        ),
    ] = None
    reporting_period_configuration_id: Annotated[
        str | None,
        Field(
            alias="reportingPeriodConfigurationId",
            description="Identifies the associated reporting period configuration. If null the analysis uses a standard reporting period.",
        ),
    ] = None
    accounting_period: Annotated[
        ApiAccountingPeriodUpdate | None,
        Field(
            alias="accountingPeriod",
            description="Details about the accounting period used in this analysis. If null the analysis uses a custom reporting period.",
        ),
    ] = None


class ApiAnalysisImportantColumnRead(BaseItem):
    column_name: Annotated[
        str | None,
        Field(
            alias="columnName",
            description="The name of the column as it appears in the imported file.",
        ),
    ] = None
    field: Annotated[
        str | None, Field(description="The name of the additional data column.")
    ] = None


class ApiAnalysisPeriodGapRead(BaseItem):
    analysis_period_id: Annotated[
        str | None,
        Field(alias="analysisPeriodId", description="Identifies the analysis period."),
    ] = None
    previous_analysis_period_id: Annotated[
        str | None,
        Field(
            alias="previousAnalysisPeriodId",
            description="Identifies the previous analysis period relevant to the current analysis period.",
        ),
    ] = None
    days: Annotated[
        int | None,
        Field(description="The number of days between two analysis periods."),
    ] = None


class ApiAnalysisPeriodRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    start_date: Annotated[
        date | None,
        Field(
            alias="startDate", description="The first day of the period under analysis."
        ),
    ] = None
    interim_as_at_date: Annotated[
        date | None,
        Field(
            alias="interimAsAtDate",
            description="The last day of the interim period under analysis.",
        ),
    ] = None
    end_date: Annotated[
        date | None,
        Field(
            alias="endDate", description="The last day of the period under analysis."
        ),
    ] = None


class ApiAnalysisRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(alias="analysisTypeId", description="Identifies the type of analysis."),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the analysis.", max_length=80, min_length=0),
    ] = None
    interim: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the analysis is using an interim time frame."
        ),
    ] = None
    archived: Annotated[
        bool | None,
        Field(description="Indicates whether or not the analysis has been archived."),
    ] = None
    converted: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not an interim analysis time frame has been converted to a full analysis time frame."
        ),
    ] = None
    periodic: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the analysis is using a periodic time frame."
        ),
    ] = None
    important_columns: Annotated[
        list[ApiAnalysisImportantColumnRead] | None,
        Field(
            alias="importantColumns",
            description="Additional data columns that can be used when importing additional data.",
        ),
    ] = None
    analysis_periods: Annotated[
        list[ApiAnalysisPeriodRead] | None,
        Field(
            alias="analysisPeriods",
            description="Details about the specific analysis periods under audit.",
        ),
    ] = None
    analysis_period_gaps: Annotated[
        list[ApiAnalysisPeriodGapRead] | None,
        Field(
            alias="analysisPeriodGaps",
            description="Details about the gap in time between two analysis periods.",
        ),
    ] = None
    currency_code: Annotated[
        str | None,
        Field(
            alias="currencyCode",
            description="The currency to be displayed across the analysis results.",
        ),
    ] = None
    latest_analysis_result_id: Annotated[
        str | None, Field(alias="latestAnalysisResultId")
    ] = None
    reference_id: Annotated[
        str | None,
        Field(
            alias="referenceId",
            description="A reference ID to identify the analysis.",
            max_length=256,
            min_length=0,
        ),
    ] = None
    reporting_period_configuration_id: Annotated[
        str | None,
        Field(
            alias="reportingPeriodConfigurationId",
            description="Identifies the associated reporting period configuration. If null the analysis uses a standard reporting period.",
        ),
    ] = None
    accounting_period: Annotated[
        ApiAccountingPeriodRead | None,
        Field(
            alias="accountingPeriod",
            description="Details about the accounting period used in this analysis. If null the analysis uses a custom reporting period.",
        ),
    ] = None


class ApiAccountMappingUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    code: Annotated[
        str | None,
        Field(description="The account grouping code mapped to this account."),
    ] = None
    account_tags: Annotated[
        list[str] | None,
        Field(
            alias="accountTags",
            description="A list of account tags associated with this account.",
        ),
    ] = None


class ApiAccountMappingReadStatus(str, Enum):
    """Indicates the current status of the account mapping."""

    MANUAL = "MANUAL"
    MAC_CODE = "MAC_CODE"
    MODIFIED_MAC = "MODIFIED_MAC"
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNMAPPED = "UNMAPPED"
    USED = "USED"
    UNUSED = "UNUSED"


class ApiAccountMappingRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    account: Annotated[
        str | None,
        Field(description="The account name as provided in the source data."),
    ] = None
    account_description: Annotated[
        str | None,
        Field(
            alias="accountDescription",
            description="The description of the account as provided in the source data.",
        ),
    ] = None
    code: Annotated[
        str | None,
        Field(description="The account grouping code mapped to this account."),
    ] = None
    status: Annotated[
        ApiAccountMappingReadStatus | None,
        Field(description="Indicates the current status of the account mapping."),
    ] = None
    used_by_analysis_sources: Annotated[
        list[str] | None,
        Field(
            alias="usedByAnalysisSources",
            description="A list of analysis sources that use this account.",
        ),
    ] = None
    fund_id: Annotated[
        str | None,
        Field(alias="fundId", description="The fund that includes this account."),
    ] = None
    account_tags: Annotated[
        list[str] | None,
        Field(
            alias="accountTags",
            description="A list of account tags associated with this account.",
        ),
    ] = None


class ApiAccountGroupUpdate(BaseItem):
    mac_code: Annotated[
        str | None,
        Field(
            alias="macCode", description="The MAC code mapped to this account group."
        ),
    ] = None
    account_tags: Annotated[
        list[str] | None,
        Field(
            alias="accountTags",
            description="A list of account tags assigned to this account group.",
        ),
    ] = None


class ApiAccountGroupRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    account_grouping_id: Annotated[
        str | None,
        Field(
            alias="accountGroupingId",
            description="The unique identifier for the account grouping that the account group belongs to.",
        ),
    ] = None
    code: Annotated[
        str | None, Field(description="The account code for this account group.")
    ] = None
    description: Annotated[
        dict[str, str] | None,
        Field(description="A description of the account code for this account group."),
    ] = None
    lowest_level: Annotated[bool | None, Field(alias="lowestLevel")] = None
    hierarchy: Annotated[
        list[str] | None,
        Field(description="A list of the parent codes for this account group."),
    ] = None
    parent_code: Annotated[
        str | None,
        Field(
            alias="parentCode", description="The parent code for this account group."
        ),
    ] = None
    mac_code: Annotated[
        str | None,
        Field(
            alias="macCode", description="The MAC code mapped to this account group."
        ),
    ] = None
    account_tags: Annotated[
        list[str] | None,
        Field(
            alias="accountTags",
            description="A list of account tags assigned to this account group.",
        ),
    ] = None
    published_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="publishedDate",
            description="The date this account group was published. If not set, this account group is not published.\n\nPublished account groups cannot be updated.",
        ),
    ] = None
    order_index: Annotated[
        int | None,
        Field(
            alias="orderIndex",
            description="The order in which this account group is displayed, relative to other account groups with the same parent.",
        ),
    ] = None
    errors: Annotated[
        list[ApiAccountGroupErrorRead] | None,
        Field(description="A list of errors associated with this account group."),
    ] = None


class ApiAccountGroupingUpdatePublishStatus(str, Enum):
    """The current status of the account grouping."""

    DRAFT = "DRAFT"
    UNPUBLISHED_CHANGES = "UNPUBLISHED_CHANGES"
    PUBLISHED = "PUBLISHED"


class ApiAccountGroupingUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    name: Annotated[
        dict[str, str] | None, Field(description="The name of the account grouping.")
    ] = None
    archived: Annotated[
        bool | None, Field(description="When `true`, the account grouping is archived.")
    ] = None
    publish_status: Annotated[
        ApiAccountGroupingUpdatePublishStatus | None,
        Field(
            alias="publishStatus",
            description="The current status of the account grouping.",
        ),
    ] = None


class ApiAccountGroupingReadPublishStatus(str, Enum):
    """The current status of the account grouping."""

    DRAFT = "DRAFT"
    UNPUBLISHED_CHANGES = "UNPUBLISHED_CHANGES"
    PUBLISHED = "PUBLISHED"


class ApiAccountGroupingRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    name: Annotated[
        dict[str, str] | None, Field(description="The name of the account grouping.")
    ] = None
    code_display_name: Annotated[
        dict[str, str] | None,
        Field(
            alias="codeDisplayName",
            description="The name of the account code hierarchy system used within the dataset.",
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The delimiter character used to separate each category level in an account grouping code."
        ),
    ] = None
    mac: Annotated[
        bool | None,
        Field(
            description="When `true`, the account grouping is based on the MAC code system."
        ),
    ] = None
    system: Annotated[
        bool | None,
        Field(
            description="When `true`, the account grouping is a system account grouping and cannot be modified."
        ),
    ] = None
    archived: Annotated[
        bool | None, Field(description="When `true`, the account grouping is archived.")
    ] = None
    published_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="publishedDate",
            description="The date that the account grouping was published.",
        ),
    ] = None
    publish_status: Annotated[
        ApiAccountGroupingReadPublishStatus | None,
        Field(
            alias="publishStatus",
            description="The current status of the account grouping.",
        ),
    ] = None


class ApiWebhookCreateEvent(str, Enum):
    EXPORT_READY = "EXPORT_READY"
    FILE_MANAGER_FILE_ADDED = "FILE_MANAGER_FILE_ADDED"
    INGESTION_COMPLETE = "INGESTION_COMPLETE"
    INGESTION_FAILED = "INGESTION_FAILED"
    INGESTION_ANALYSIS_COMPLETE = "INGESTION_ANALYSIS_COMPLETE"
    INGESTION_ANALYSIS_FAILED = "INGESTION_ANALYSIS_FAILED"
    UNMAPPED_ACCOUNTS_DETECTED = "UNMAPPED_ACCOUNTS_DETECTED"
    ENGAGEMENT_CREATED = "ENGAGEMENT_CREATED"
    ENGAGEMENT_UPDATED = "ENGAGEMENT_UPDATED"
    ENGAGEMENT_DELETED = "ENGAGEMENT_DELETED"
    ANALYSIS_CREATED = "ANALYSIS_CREATED"
    ANALYSIS_UPDATED = "ANALYSIS_UPDATED"
    ANALYSIS_DELETED = "ANALYSIS_DELETED"
    ANALYSIS_ARCHIVED = "ANALYSIS_ARCHIVED"
    ANALYSIS_UNARCHIVED = "ANALYSIS_UNARCHIVED"
    USER_INVITED = "USER_INVITED"
    USER_STATUS_UPDATED = "USER_STATUS_UPDATED"
    USER_ROLE_UPDATED = "USER_ROLE_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_LOGIN = "USER_LOGIN"


class ApiWebhookCreateStatus(str, Enum):
    """The current status of the webhook."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ApiWebhookCreate(BaseItem):
    name: Annotated[str | None, Field(description="The name of the webhook.")] = None
    url: Annotated[
        str | None,
        Field(description="The URL to which the webhook will send notifications."),
    ] = None
    technical_contact_id: Annotated[
        str | None,
        Field(
            alias="technicalContactId",
            description="A reference to an administrative user used to inform system administrators of issues with the webhooks.",
        ),
    ] = None
    events: Annotated[
        list[ApiWebhookCreateEvent] | None,
        Field(
            description="A list of events that will trigger this webhook.",
            max_length=2147483647,
            min_length=1,
        ),
    ] = None
    status: Annotated[
        ApiWebhookCreateStatus | None,
        Field(description="The current status of the webhook."),
    ] = None


class SortnullRead(BaseItem):
    sorted: bool | None = None
    unsorted: bool | None = None
    empty: bool | None = None


class ApiWebhookEventLogReadStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FAILED_PERMANENTLY = "FAILED_PERMANENTLY"
    DISCONNECTED = "DISCONNECTED"


class ApiWebhookEventLogRead(BaseItem):
    id: str | None = None
    version: int | None = None
    creation_date: Annotated[AwareDatetime | None, Field(alias="creationDate")] = None
    last_modified_date: Annotated[
        AwareDatetime | None, Field(alias="lastModifiedDate")
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None, Field(alias="createdUserInfo")
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None, Field(alias="lastModifiedUserInfo")
    ] = None
    status: ApiWebhookEventLogReadStatus | None = None
    webhook_id: Annotated[str | None, Field(alias="webhookId")] = None
    attempt_start_date: Annotated[
        AwareDatetime | None, Field(alias="attemptStartDate")
    ] = None
    url: str | None = None
    event_type: Annotated[str | None, Field(alias="eventType")] = None
    request_headers: Annotated[
        dict[str, list[str]] | None, Field(alias="requestHeaders")
    ] = None
    request_body: Annotated[str | None, Field(alias="requestBody")] = None
    response_status_code: Annotated[int | None, Field(alias="responseStatusCode")] = (
        None
    )
    response_headers: Annotated[
        dict[str, list[str]] | None, Field(alias="responseHeaders")
    ] = None
    response_time_sec: Annotated[float | None, Field(alias="responseTimeSec")] = None
    retry_count: Annotated[int | None, Field(alias="retryCount")] = None
    request_id: Annotated[str | None, Field(alias="requestId")] = None


class ApiUserCreateRole(str, Enum):
    """The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"""

    ROLE_ADMIN = "ROLE_ADMIN"
    ROLE_ORGANIZATION_ADMIN = "ROLE_ORGANIZATION_ADMIN"
    ROLE_USER = "ROLE_USER"
    ROLE_CLIENT = "ROLE_CLIENT"
    ROLE_MINDBRIDGE_SUPPORT = "ROLE_MINDBRIDGE_SUPPORT"
    ROLE_USER_ADMIN = "ROLE_USER_ADMIN"


class ApiUserCreate(BaseItem):
    email: Annotated[str | None, Field(description="The user's email address.")] = None
    role: Annotated[
        ApiUserCreateRole | None,
        Field(
            description="The MindBridge role assigned to the user. [Learn about user roles](https://support.mindbridge.ai/hc/en-us/articles/360056394954-User-roles-available-in-MindBridge)"
        ),
    ] = None


class ApiTransactionIdPreviewIndicatorReadRating(str, Enum):
    """The quality of the indicator as rated by MindBridge."""

    BLOCK = "BLOCK"
    FAIL = "FAIL"
    POOR = "POOR"
    NEUTRAL = "NEUTRAL"
    GOOD = "GOOD"


class ApiTransactionIdPreviewRowRead(BaseItem):
    transaction_id: Annotated[
        str | None,
        Field(
            alias="transactionId",
            description="Identifies the transaction ID for this transaction.",
        ),
    ] = None
    balance: Annotated[
        int | None, Field(description="The balance of the transaction.")
    ] = None
    entry_count: Annotated[
        int | None,
        Field(
            alias="entryCount",
            description="The number of entries that appear within the transaction.",
        ),
    ] = None
    detail_rows: Annotated[
        list[dict[str, Any]] | None,
        Field(
            alias="detailRows",
            description="The set of entries that appear within the transaction.",
        ),
    ] = None


class ApiTransactionIdPreviewReadType(str, Enum):
    """The type used when selecting a transaction ID."""

    COMBINATION = "COMBINATION"
    RUNNING_TOTAL = "RUNNING_TOTAL"


class ApiTransactionIdPreviewReadOverallRating(str, Enum):
    """The quality of the transaction ID as rated by MindBridge."""

    BLOCK = "BLOCK"
    FAIL = "FAIL"
    POOR = "POOR"
    NEUTRAL = "NEUTRAL"
    GOOD = "GOOD"


class ApiTaskCreateStatus(str, Enum):
    """The current state of the task."""

    OPEN = "OPEN"
    NORMAL = "NORMAL"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class ApiTaskCreateType(str, Enum):
    """The type of entry this task is associated with."""

    ENTRY = "ENTRY"
    TRANSACTION = "TRANSACTION"
    AP_ENTRY = "AP_ENTRY"
    AR_ENTRY = "AR_ENTRY"
    AP_OUTSTANDING_ENTRY = "AP_OUTSTANDING_ENTRY"
    AR_OUTSTANDING_ENTRY = "AR_OUTSTANDING_ENTRY"
    TRA_ENTRY = "TRA_ENTRY"
    SUBLEDGER_ENTRY = "SUBLEDGER_ENTRY"


class ApiTaskCreateTaskApprovalStatus(str, Enum):
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"


class ApiTaskCreate(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_result_id: Annotated[str | None, Field(alias="analysisResultId")] = None
    row_id: Annotated[
        int | None, Field(alias="rowId", description="Identifies the associated entry.")
    ] = None
    transaction_id: Annotated[
        int | None,
        Field(
            alias="transactionId", description="Identifies the associated transaction."
        ),
    ] = None
    status: Annotated[
        ApiTaskCreateStatus | None,
        Field(description="The current state of the task.", title="Task Status"),
    ] = None
    assigned_id: Annotated[
        str | None,
        Field(
            alias="assignedId", description="Identifies the user assigned to this task."
        ),
    ] = None
    description: Annotated[
        str | None, Field(description="A description of the task.")
    ] = None
    sample: Annotated[
        str | None, Field(description="Which sample this task is a part of.")
    ] = None
    audit_areas: Annotated[
        list[str] | None,
        Field(
            alias="auditAreas",
            description="Which audit areas this task is associated with.",
        ),
    ] = None
    assertions: Annotated[
        list[str] | None,
        Field(description="Which assertions this task is associated with."),
    ] = None
    type: Annotated[
        ApiTaskCreateType | None,
        Field(
            description="The type of entry this task is associated with.",
            title="Task Type",
        ),
    ] = None
    task_approval_status: Annotated[
        ApiTaskCreateTaskApprovalStatus | None,
        Field(alias="taskApprovalStatus", title="Task Approval Status"),
    ] = None
    due_date: Annotated[date | None, Field(alias="dueDate")] = None
    tags: list[str] | None = None


class ApiTaskCommentCreate(BaseItem):
    comment_text: Annotated[
        str | None, Field(alias="commentText", description="The text of the comment.")
    ] = None


class ApiTaskHistoryEntryReadFieldType(str, Enum):
    ARRAY = "ARRAY"
    ISO_DATE = "ISO_DATE"
    OBJECT = "OBJECT"
    STRING = "STRING"
    INTEGER = "INTEGER"


class ApiTaskHistoryEntryRead(BaseItem):
    field_name: Annotated[str | None, Field(alias="fieldName")] = None
    field_type: Annotated[
        ApiTaskHistoryEntryReadFieldType | None, Field(alias="fieldType")
    ] = None
    previous_value: Annotated[Any | None, Field(alias="previousValue")] = None
    new_value: Annotated[Any | None, Field(alias="newValue")] = None
    previous_value_string: Annotated[str | None, Field(alias="previousValueString")] = (
        None
    )
    new_value_string: Annotated[str | None, Field(alias="newValueString")] = None


class ApiTaskHistoryReadOperation(str, Enum):
    """The operation that was performed on the task."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    COMPLETED = "COMPLETED"
    DELETE = "DELETE"
    COMMENT = "COMMENT"
    ASSIGNMENT = "ASSIGNMENT"
    STATUS_CHANGE = "STATUS_CHANGE"
    MARKASNORMAL = "MARKASNORMAL"


class ApiTaskHistoryRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    date_time: Annotated[
        AwareDatetime | None,
        Field(
            alias="dateTime",
            description="The date and time that the task history was created.",
        ),
    ] = None
    user_name: Annotated[
        str | None,
        Field(
            alias="userName",
            description="Name of the user associated with the history record",
        ),
    ] = None
    task_id: Annotated[
        str | None, Field(alias="taskId", description="Identifies the associated task.")
    ] = None
    user_id: Annotated[
        str | None,
        Field(
            alias="userId",
            description="The id of the user associated with the history record",
        ),
    ] = None
    operation: Annotated[
        ApiTaskHistoryReadOperation | None,
        Field(description="The operation that was performed on the task."),
    ] = None
    changes: Annotated[
        list[ApiTaskHistoryEntryRead] | None,
        Field(description="A list of changes that were made to the task."),
    ] = None


class ApiFilterConditionCreateType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterGroupConditionCreateType(str, Enum):
    """The type of condition."""

    GROUP = "GROUP"
    STRING = "STRING"
    STRING_ARRAY = "STRING_ARRAY"
    CONTROL_POINT = "CONTROL_POINT"
    ACCOUNT_NODE_ARRAY = "ACCOUNT_NODE_ARRAY"
    TYPEAHEAD_ENTRY = "TYPEAHEAD_ENTRY"
    POPULATIONS = "POPULATIONS"
    RISK_SCORE = "RISK_SCORE"
    MONETARY_FLOW = "MONETARY_FLOW"
    MONEY = "MONEY"
    MATERIALITY = "MATERIALITY"
    NUMERICAL = "NUMERICAL"
    DATE = "DATE"


class ApiFilterGroupConditionCreateOperator(str, Enum):
    """The operator to be applied to conditions within this group."""

    AND = "AND"
    OR = "OR"


class ApiFilterCreateFilterType(str, Enum):
    """The type of this filter. Determines in which context analyses can access it."""

    LIBRARY = "LIBRARY"
    ORGANIZATION = "ORGANIZATION"
    PRIVATE = "PRIVATE"
    ENGAGEMENT = "ENGAGEMENT"


class ApiFilterCreateDataType(str, Enum):
    """The intended data type for this filter."""

    TRANSACTIONS = "TRANSACTIONS"
    ENTRIES = "ENTRIES"
    LIBRARY = "LIBRARY"


class ApiFilterValidateRequestCreate(BaseItem):
    filter_id: Annotated[str | None, Field(alias="filterId")] = None
    data_table_id: Annotated[str | None, Field(alias="dataTableId")] = None


class ApiRiskRangeBoundsCreate(BaseItem):
    low_threshold: Annotated[
        int | None,
        Field(
            alias="lowThreshold",
            description="The low threshold of the risk range.",
            ge=0,
            le=10000,
        ),
    ] = None
    high_threshold: Annotated[
        int | None,
        Field(
            alias="highThreshold",
            description="The high threshold of the risk range.",
            ge=0,
            le=10000,
        ),
    ] = None


class ApiRiskRangesCreate(BaseItem):
    low: Annotated[
        ApiRiskRangeBoundsCreate | None, Field(description="The low range bounds.")
    ] = None
    medium: Annotated[
        ApiRiskRangeBoundsCreate | None, Field(description="The medium range bounds.")
    ] = None
    high: Annotated[
        ApiRiskRangeBoundsCreate | None, Field(description="The high range bounds.")
    ] = None
    library_id: Annotated[
        str | None,
        Field(
            alias="libraryId",
            description="Identifies the library associated with this risk range.",
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(
            alias="analysisTypeId",
            description="Identifies the analysis type associated with this risk range.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the risk range.", max_length=80, min_length=0),
    ] = None
    description: Annotated[
        str | None,
        Field(
            description="The description of the risk range.",
            max_length=250,
            min_length=0,
        ),
    ] = None


class ApiMonthlyReportingPeriodCreate(BaseItem):
    period_number: Annotated[int | None, Field(alias="periodNumber")] = None
    quarter_number: Annotated[int | None, Field(alias="quarterNumber")] = None
    year_label: Annotated[str | None, Field(alias="yearLabel")] = None
    start_date: Annotated[date | None, Field(alias="startDate")] = None
    end_date: Annotated[date | None, Field(alias="endDate")] = None


class ApiWeeklyReportingPeriodCreate(BaseItem):
    week_number: Annotated[int | None, Field(alias="weekNumber")] = None
    year_label: Annotated[str | None, Field(alias="yearLabel")] = None
    start_date: Annotated[date | None, Field(alias="startDate")] = None
    end_date: Annotated[date | None, Field(alias="endDate")] = None


class ApiMonthlyReportingPeriodRead(BaseItem):
    period_number: Annotated[int | None, Field(alias="periodNumber")] = None
    quarter_number: Annotated[int | None, Field(alias="quarterNumber")] = None
    year_label: Annotated[str | None, Field(alias="yearLabel")] = None
    start_date: Annotated[date | None, Field(alias="startDate")] = None
    end_date: Annotated[date | None, Field(alias="endDate")] = None


class ApiReportingPeriodConfigurationReadStatus(str, Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class ApiWeeklyReportingPeriodRead(BaseItem):
    week_number: Annotated[int | None, Field(alias="weekNumber")] = None
    year_label: Annotated[str | None, Field(alias="yearLabel")] = None
    start_date: Annotated[date | None, Field(alias="startDate")] = None
    end_date: Annotated[date | None, Field(alias="endDate")] = None


class ApiOrganizationCreate(BaseItem):
    name: Annotated[
        str | None,
        Field(description="The name of the organization.", max_length=80, min_length=0),
    ] = None
    external_client_code: Annotated[
        str | None,
        Field(
            alias="externalClientCode",
            description="The unique client ID applied to this organization.",
            max_length=80,
            min_length=0,
        ),
    ] = None
    manager_user_ids: Annotated[
        list[str] | None,
        Field(
            alias="managerUserIds",
            description="Identifies users assigned to the organization manager role.",
        ),
    ] = None


class ApiLibraryCreateRiskScoreDisplay(str, Enum):
    """Determines whether risk scores will be presented as percentages (%), or using High, Medium, and Low label indicators."""

    HIGH_MEDIUM_LOW = "HIGH_MEDIUM_LOW"
    PERCENTAGE = "PERCENTAGE"


class ApiLibraryCreate(BaseItem):
    name: Annotated[
        str | None,
        Field(
            description="The current name of the library.", max_length=80, min_length=0
        ),
    ] = None
    based_on_library_id: Annotated[
        str | None,
        Field(
            alias="basedOnLibraryId",
            description="Identifies the library that the new library is based on. This may be a user-created library or a MindBridge system library.",
        ),
    ] = None
    convert_settings: Annotated[
        bool | None,
        Field(
            alias="convertSettings",
            description="Indicates whether or not settings from the selected base library should be converted for use with the selected account grouping.",
        ),
    ] = None
    warnings_dismissed: Annotated[
        bool | None,
        Field(
            alias="warningsDismissed",
            description="When set to `true`, any conversion warnings for this library will not be displayed in the **Libraries** tab in the UI.",
        ),
    ] = None
    account_grouping_id: Annotated[
        str | None,
        Field(
            alias="accountGroupingId",
            description="Identifies the account grouping used.",
        ),
    ] = None
    analysis_type_ids: Annotated[
        list[str] | None,
        Field(
            alias="analysisTypeIds",
            description="Identifies the analysis types used in the library.",
        ),
    ] = None
    default_delimiter: Annotated[
        str | None,
        Field(
            alias="defaultDelimiter",
            description="Identifies the default delimiter used in imported CSV files.",
        ),
    ] = None
    control_point_selection_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointSelectionPermission",
            description="When set to `true`, control points can be added or removed within each risk score.",
        ),
    ] = None
    control_point_weight_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointWeightPermission",
            description="When set to `true`, the weight of each control point can be adjusted within each risk score.",
        ),
    ] = None
    control_point_settings_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointSettingsPermission",
            description="When set to `true`, individual control point settings can be adjusted within each risk score.",
        ),
    ] = None
    risk_score_and_groups_selection_permission: Annotated[
        bool | None,
        Field(
            alias="riskScoreAndGroupsSelectionPermission",
            description="When set to `true`, risk scores and groups can be disabled, and accounts associated with risk scores can be edited.",
        ),
    ] = None
    risk_range_edit_permission: Annotated[
        bool | None, Field(alias="riskRangeEditPermission")
    ] = None
    risk_score_display: Annotated[
        ApiLibraryCreateRiskScoreDisplay | None,
        Field(
            alias="riskScoreDisplay",
            description="Determines whether risk scores will be presented as percentages (%), or using High, Medium, and Low label indicators.",
        ),
    ] = None


class ApiJsonTableRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    headers: list[str] | None = None
    current_size: Annotated[
        int | None,
        Field(
            alias="currentSize",
            description="The combined size of all data that has been appended to this JSON table.",
        ),
    ] = None


class ApiFileExportRead(BaseItem):
    id: Annotated[
        str | None, Field(description="The unique file export identifier.")
    ] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the file export.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the file export.",
        ),
    ] = None
    file_name: Annotated[
        str | None, Field(alias="fileName", description="The name of the file.")
    ] = None
    size: Annotated[int | None, Field(description="The size of the file.")] = None


class ApiFileManagerDirectoryCreate(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    parent_file_manager_entity_id: Annotated[
        str | None,
        Field(
            alias="parentFileManagerEntityId",
            description="Identifies the parent directory. If NULL, the directory is positioned at the root level.",
        ),
    ] = None
    name: Annotated[str | None, Field(description="The name of the directory.")] = None


class FileMergeMappingCreate(BaseItem):
    file_manager_file_id: Annotated[
        str | None,
        Field(
            alias="fileManagerFileId", description="The file manager file id to merge"
        ),
    ] = None
    columns: Annotated[
        list[int] | None,
        Field(description="Columns to include from this file, in order"),
    ] = None


class CreateApiFileManagerFileFromJsonTableRequestCreate(BaseItem):
    name: Annotated[
        str | None,
        Field(description="The name of the newly created file manager file."),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="Identifies the associated engagement to import the formatted file into.",
        ),
    ] = None
    parent_file_manager_entity_id: Annotated[
        str | None,
        Field(
            alias="parentFileManagerEntityId",
            description="Identifies the file manager entity that will be the parent of the newly created file.",
        ),
    ] = None
    json_table_id: Annotated[
        str | None,
        Field(
            alias="jsonTableId",
            description="Identifies the JSON table to be formatted into a file.",
        ),
    ] = None


class ApiCsvConfigurationCreate(BaseItem):
    delimiter: Annotated[
        str | None, Field(description="The character used to separate entries.")
    ] = None
    quote: Annotated[
        str | None, Field(description="The character used to encapsulate an entry.")
    ] = None
    quote_escape: Annotated[
        str | None,
        Field(
            alias="quoteEscape",
            description="The character used to escape the quote character.",
        ),
    ] = None
    quote_escape_escape: Annotated[
        str | None,
        Field(
            alias="quoteEscapeEscape",
            description="The character used to escape the quote escape character.",
        ),
    ] = None


class ApiDataTableQuerySortOrderCreateDirection(str, Enum):
    """How the column will be sorted."""

    ASC = "ASC"
    DESC = "DESC"


class ApiDataTableQuerySortOrderCreate(BaseItem):
    field: Annotated[str | None, Field(description="The data table column.")] = None
    direction: Annotated[
        ApiDataTableQuerySortOrderCreateDirection | None,
        Field(description="How the column will be sorted."),
    ] = None


class ShieldQueryTermCreateOperatorShieldQueryTermCreateOperatorEnum(str, Enum):
    FIELD_EQ = "$eq"
    FIELD_NE = "$ne"
    FIELD_GT = "$gt"
    FIELD_GTE = "$gte"
    FIELD_LT = "$lt"
    FIELD_LTE = "$lte"
    FIELD_CONTAINS = "$contains"
    FIELD_NCONTAINS = "$ncontains"
    FIELD_IN = "$in"
    FIELD_NIN = "$nin"
    FIELD_FLAGS = "$flags"
    FIELD_KEYWORD_PREFIX = "$keyword_prefix"
    FIELD_KEYWORD_PREFIX_NOT = "$keyword_prefix_not"
    FIELD_ISUBSTR = "$isubstr"
    FIELD_IPREFIX = "$iprefix"
    FIELD_NIPREFIX = "$niprefix"
    FIELD_BETWEEN = "$between"
    FIELD_NBETWEEN = "$nbetween"
    FIELD_AND = "$and"
    FIELD_OR = "$or"
    FIELD_POPULATION = "$population"
    FIELD_NOT_POPULATION = "$not_population"


ShieldQueryTermCreateOperator = RootModel[
    ShieldQueryTermCreateOperatorShieldQueryTermCreateOperatorEnum | None
]


class ShieldQueryTermCreate(BaseItem):
    operator: ShieldQueryTermCreateOperator | None = None


class ApiFileManagerFileCreate(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    parent_file_manager_entity_id: Annotated[
        str | None,
        Field(
            alias="parentFileManagerEntityId",
            description="Identifies the parent directory. If NULL, the directory is positioned at the root level.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The current name of the file, excluding the extension."),
    ] = None


class CreateApiFileManagerFileFromChunkedFileRequestCreate(BaseItem):
    chunked_file_id: Annotated[str | None, Field(alias="chunkedFileId")] = None
    api_file_manager_file: Annotated[
        ApiFileManagerFileCreate | None, Field(alias="apiFileManagerFile")
    ] = None


class ApiBasicMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiColumnDateTimeFormatRead(BaseItem):
    selected: Annotated[
        bool | None,
        Field(
            description="If true, this format was selected during column mapping as the correct format for this column."
        ),
    ] = None
    custom_format_pattern: Annotated[
        str | None,
        Field(
            alias="customFormatPattern", description="The pattern of this date format."
        ),
    ] = None
    sample_raw_values: Annotated[
        list[str] | None,
        Field(alias="sampleRawValues", description="A list of values in this column."),
    ] = None
    sample_converted_values: Annotated[
        list[AwareDatetime] | None,
        Field(
            alias="sampleConvertedValues",
            description="A list of date time values derived by parsing the text using this format.",
        ),
    ] = None


class ApiCountMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiCurrencyFormatRead(BaseItem):
    decimal_character: Annotated[
        str | None,
        Field(
            alias="decimalCharacter",
            description="The character used as a decimal separator.",
        ),
    ] = None
    non_decimal_delimiters: Annotated[
        list[str] | None,
        Field(
            alias="nonDecimalDelimiters",
            description="Non decimal separator special characters, including currency and grouping characters.",
        ),
    ] = None
    ambiguous_delimiters: Annotated[
        list[str] | None,
        Field(
            alias="ambiguousDelimiters",
            description="A list of possible delimiter characters, if multiple possible candidates are available.",
        ),
    ] = None
    example: Annotated[str | None, Field(description="An example value.")] = None


class ApiDataPreviewRead(BaseItem):
    row: Annotated[
        int | None, Field(description="The row number within the table.")
    ] = None
    column: Annotated[
        int | None, Field(description="The column index within the row.")
    ] = None
    data: Annotated[
        str | None, Field(description="The value within the target row.")
    ] = None


class ApiDataTypeMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiDataTypeMetricsReadDetectedType(str, Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    UNKNOWN = "UNKNOWN"
    FLOAT64 = "FLOAT64"


class ApiDataTypeMetricsReadDominantType(str, Enum):
    """The type determined to be the most prevalent in this column."""

    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    UNKNOWN = "UNKNOWN"
    FLOAT64 = "FLOAT64"


class ApiDensityMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiDensityMetricsRead(BaseItem):
    state: Annotated[
        ApiDensityMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )
    density: Annotated[
        float | None,
        Field(
            description="The percentage density of values against blanks, represented as decimal between 1 and 0."
        ),
    ] = None
    blanks: Annotated[int | None, Field(description="The number of blank values.")] = (
        None
    )


class ApiDistinctValueMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiDistinctValueMetricsRead(BaseItem):
    state: Annotated[
        ApiDistinctValueMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )


class ApiFileInfoType(str, Enum):
    """The type of file info entity."""

    FILE_INFO = "FILE_INFO"
    TABULAR_FILE_INFO = "TABULAR_FILE_INFO"


class ApiFileInfoFormat(str, Enum):
    """The grouped format that was detected."""

    QUICKBOOKS_JOURNAL = "QUICKBOOKS_JOURNAL"
    QUICKBOOKS_JOURNAL_2024 = "QUICKBOOKS_JOURNAL_2024"
    QUICKBOOKS_TRANSACTION_DETAIL_BY_ACCOUNT = (
        "QUICKBOOKS_TRANSACTION_DETAIL_BY_ACCOUNT"
    )
    SAGE50_LEDGER = "SAGE50_LEDGER"
    SAGE50_TRANSACTIONS = "SAGE50_TRANSACTIONS"
    CCH_ACCOUNT_LIST = "CCH_ACCOUNT_LIST"
    MS_DYNAMICS_JOURNAL = "MS_DYNAMICS_JOURNAL"
    SAGE50_UK = "SAGE50_UK"


class ApiFileInfo(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    type: Annotated[
        ApiFileInfoType | None,
        Field(description="The type of file info entity.", title="File Info Type"),
    ] = None
    name: Annotated[
        str | None, Field(description="The name of the underlying file or table.")
    ] = None
    format_detected: Annotated[
        bool | None,
        Field(
            alias="formatDetected",
            description="When `true` a known grouped format was detected.",
        ),
    ] = None
    format: Annotated[
        ApiFileInfoFormat | None,
        Field(description="The grouped format that was detected."),
    ] = None


class ApiFileInfoReadType(str, Enum):
    """The type of file info entity."""

    FILE_INFO = "FILE_INFO"
    TABULAR_FILE_INFO = "TABULAR_FILE_INFO"


class ApiFileInfoReadFormat(str, Enum):
    """The grouped format that was detected."""

    QUICKBOOKS_JOURNAL = "QUICKBOOKS_JOURNAL"
    QUICKBOOKS_JOURNAL_2024 = "QUICKBOOKS_JOURNAL_2024"
    QUICKBOOKS_TRANSACTION_DETAIL_BY_ACCOUNT = (
        "QUICKBOOKS_TRANSACTION_DETAIL_BY_ACCOUNT"
    )
    SAGE50_LEDGER = "SAGE50_LEDGER"
    SAGE50_TRANSACTIONS = "SAGE50_TRANSACTIONS"
    CCH_ACCOUNT_LIST = "CCH_ACCOUNT_LIST"
    MS_DYNAMICS_JOURNAL = "MS_DYNAMICS_JOURNAL"
    SAGE50_UK = "SAGE50_UK"


class ApiFileInfoRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    type: Annotated[
        ApiFileInfoReadType | None,
        Field(description="The type of file info entity.", title="File Info Type"),
    ] = None
    name: Annotated[
        str | None, Field(description="The name of the underlying file or table.")
    ] = None
    format_detected: Annotated[
        bool | None,
        Field(
            alias="formatDetected",
            description="When `true` a known grouped format was detected.",
        ),
    ] = None
    format: Annotated[
        ApiFileInfoReadFormat | None,
        Field(description="The grouped format that was detected."),
    ] = None


class ApiHistogramMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiHistogramMetricsRead(BaseItem):
    state: Annotated[
        ApiHistogramMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )
    histogram: Annotated[
        dict[str, int] | None,
        Field(
            description="A map of the number of columns to the number of rows with that many columns, in the case of unevenColumnsMetrics."
        ),
    ] = None


class ApiOverallDataTypeMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiOverallDataTypeMetricsRead(BaseItem):
    state: Annotated[
        ApiOverallDataTypeMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    cell_type_counts: Annotated[
        dict[str, int] | None,
        Field(
            alias="cellTypeCounts",
            description="A map of data types to the number of cells in the table of that data type.",
        ),
    ] = None
    column_type_counts: Annotated[
        dict[str, int] | None,
        Field(
            alias="columnTypeCounts",
            description="A map of data types to the number of columns in the table of that data type.",
        ),
    ] = None
    total_records: Annotated[
        int | None,
        Field(alias="totalRecords", description="The total number of values."),
    ] = None
    blank_records: Annotated[
        int | None,
        Field(alias="blankRecords", description="The number of blank values."),
    ] = None
    column_count: Annotated[
        int | None, Field(alias="columnCount", description="The number of columns.")
    ] = None
    total_rows: Annotated[
        int | None, Field(alias="totalRows", description="The total number of rows.")
    ] = None


class ApiSheetMetricsReadState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiSheetMetricsRead(BaseItem):
    state: Annotated[
        ApiSheetMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )
    sheet_names: Annotated[
        list[str] | None,
        Field(
            alias="sheetNames",
            description="A list of sheet names within the underlying Excel file.",
        ),
    ] = None
    valid_sheets: Annotated[
        list[str] | None,
        Field(
            alias="validSheets",
            description="A list of usable sheet names within the underlying Excel file.",
        ),
    ] = None


class RangeBigDecimalRead(BaseItem):
    min: float | None = None
    max: float | None = None


class RangeIntegerRead(BaseItem):
    min: int | None = None
    max: int | None = None


class RangeZonedDateTimeRead(BaseItem):
    min: AwareDatetime | None = None
    max: AwareDatetime | None = None


class ApiAccountingPeriodCreateFrequency(str, Enum):
    """The frequency with which your client's financial data is reported."""

    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    THIRTEEN_PERIODS = "THIRTEEN_PERIODS"


class ApiAccountingPeriodCreate(BaseItem):
    fiscal_start_month: Annotated[
        int | None,
        Field(
            alias="fiscalStartMonth",
            description="The month that the fiscal period begins.",
        ),
    ] = None
    fiscal_start_day: Annotated[
        int | None,
        Field(
            alias="fiscalStartDay",
            description="The date of the month that the fiscal period begins.",
        ),
    ] = None
    frequency: Annotated[
        ApiAccountingPeriodCreateFrequency | None,
        Field(
            description="The frequency with which your client's financial data is reported."
        ),
    ] = None


class ApiEngagementCreate(BaseItem):
    organization_id: Annotated[
        str | None,
        Field(alias="organizationId", description="Identifies the organization."),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the engagement.", max_length=80, min_length=0),
    ] = None
    billing_code: Annotated[
        str | None,
        Field(
            alias="billingCode",
            description="A unique code that associates engagements and analyses with clients to ensure those clients are billed appropriately for MindBridge usage.",
        ),
    ] = None
    library_id: Annotated[
        str | None, Field(alias="libraryId", description="Identifies the library.")
    ] = None
    accounting_period: Annotated[
        ApiAccountingPeriodCreate | None,
        Field(
            alias="accountingPeriod", description="Details about the accounting period."
        ),
    ] = None
    audit_period_end_date: Annotated[
        date | None,
        Field(
            alias="auditPeriodEndDate",
            description="The last day of the occurring audit.",
        ),
    ] = None
    accounting_package: Annotated[
        str | None,
        Field(
            alias="accountingPackage",
            description="The ERP or financial management system that your client is using.",
        ),
    ] = None
    industry: Annotated[
        str | None,
        Field(description="The type of industry that your client operates within."),
    ] = None
    engagement_lead_id: Annotated[
        str | None,
        Field(
            alias="engagementLeadId",
            description="Identifies the user who will lead the engagement.",
        ),
    ] = None
    settings_based_on_engagement_id: Annotated[
        str | None,
        Field(
            alias="settingsBasedOnEngagementId",
            description="Identifies the engagement that the settings are based on.",
        ),
    ] = None
    reporting_period_configuration_id: Annotated[
        str | None,
        Field(
            alias="reportingPeriodConfigurationId",
            description="Identifies the associated reporting period configuration. If null the analyses use a standard reporting period.",
        ),
    ] = None
    auditor_ids: Annotated[
        list[str] | None,
        Field(
            alias="auditorIds",
            description="Identifies the users who will act as auditors in the engagement.",
        ),
    ] = None


class ApiEngagementAccountGroupCreate(BaseItem):
    engagement_account_grouping_id: Annotated[
        str | None,
        Field(
            alias="engagementAccountGroupingId",
            description="The unique identifier for the engagement account grouping that the engagement account group belongs to.",
        ),
    ] = None
    code: Annotated[
        str | None, Field(description="The account code for this account group.")
    ] = None
    description: Annotated[
        dict[str, str] | None,
        Field(description="A description of the account code for this account group."),
    ] = None
    parent_code: Annotated[
        str | None,
        Field(
            alias="parentCode", description="The parent code for this account group."
        ),
    ] = None
    mac_code: Annotated[
        str | None,
        Field(
            alias="macCode", description="The MAC code mapped to this account group."
        ),
    ] = None
    hidden: Annotated[
        bool | None,
        Field(
            description="When `true` this account is hidden, and can't be used in account mapping. Additionally this account won't be suggested when automatically mapping accounts during file import."
        ),
    ] = None
    alias: Annotated[
        str | None,
        Field(
            description="A replacement value used when displaying the account description.\n\nThis does not have any effect on automatic column mapping."
        ),
    ] = None


class ApiAsyncResultType(str, Enum):
    """Indicates the type of job being run."""

    ANALYSIS_RUN = "ANALYSIS_RUN"
    ANALYSIS_SOURCE_INGESTION = "ANALYSIS_SOURCE_INGESTION"
    ADMIN_REPORT = "ADMIN_REPORT"
    DATA_TABLE_EXPORT = "DATA_TABLE_EXPORT"
    ANALYSIS_ROLL_FORWARD = "ANALYSIS_ROLL_FORWARD"
    GDPDU_UNPACK_JOB = "GDPDU_UNPACK_JOB"
    ACCOUNT_GROUPING_EXPORT = "ACCOUNT_GROUPING_EXPORT"
    ACCOUNT_MAPPING_EXPORT = "ACCOUNT_MAPPING_EXPORT"
    DATA_TRANSFORMATION_JOB = "DATA_TRANSFORMATION_JOB"
    CONNECTION_TEST = "CONNECTION_TEST"
    CONNECTION_TABLES = "CONNECTION_TABLES"
    DATA_TABLE = "DATA_TABLE"


class ApiAsyncResultStatus(str, Enum):
    """Indicates the current state of the job."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class ApiAsyncResultEntityType(str, Enum):
    """Identifies the entity type used in the job."""

    ORGANIZATION = "ORGANIZATION"
    ENGAGEMENT = "ENGAGEMENT"
    ANALYSIS = "ANALYSIS"
    ANALYSIS_RESULT = "ANALYSIS_RESULT"
    ANALYSIS_SOURCE = "ANALYSIS_SOURCE"
    FILE_RESULT = "FILE_RESULT"
    GDPDU_UNPACK_JOB = "GDPDU_UNPACK_JOB"
    ACCOUNT_GROUPING = "ACCOUNT_GROUPING"
    ENGAGEMENT_ACCOUNT_GROUPING = "ENGAGEMENT_ACCOUNT_GROUPING"
    FILE_MANAGER_FILE = "FILE_MANAGER_FILE"
    CONNECTION_TEST_RESULT = "CONNECTION_TEST_RESULT"
    CONNECTION_TABLES_RESULT = "CONNECTION_TABLES_RESULT"
    DATA_TABLE = "DATA_TABLE"


class ApiUserInfo(BaseItem):
    user_id: Annotated[
        str | None, Field(alias="userId", description="Identifies the user.")
    ] = None
    user_name: Annotated[
        str | None, Field(alias="userName", description="The name of the user.")
    ] = None


class ApiEngagementAccountGroupingRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="The unique identifier of the engagement that this engagement account grouping belongs to.",
        ),
    ] = None
    account_grouping_id: Annotated[
        str | None,
        Field(
            alias="accountGroupingId",
            description="The unique identifier of the account grouping on which this is based.",
        ),
    ] = None
    name: Annotated[
        dict[str, str] | None, Field(description="The name of the account grouping.")
    ] = None
    code_display_name: Annotated[
        dict[str, str] | None,
        Field(
            alias="codeDisplayName",
            description="The name of the account code hierarchy system used within the dataset.",
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The delimiter character used to separate each category level in an account grouping code."
        ),
    ] = None


class ApiDatabricksAuthorizationCreateAuthType(str, Enum):
    """The authentication method to use. Possible values: PAT, OAUTH_M2M."""

    PAT = "PAT"
    OAUTH_M2_M = "OAUTH_M2M"


class ApiDatabricksAuthorizationCreate(BaseItem):
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection this authorization belongs to.",
        ),
    ] = None
    auth_type: Annotated[
        ApiDatabricksAuthorizationCreateAuthType | None,
        Field(
            alias="authType",
            description="The authentication method to use. Possible values: PAT, OAUTH_M2M.",
        ),
    ] = None
    host: Annotated[
        str | None, Field(description="The Databricks server hostname.")
    ] = None
    port: Annotated[
        int | None,
        Field(
            description="The port number for the Databricks connection. Typically 443."
        ),
    ] = None
    http_path: Annotated[
        str | None,
        Field(
            alias="httpPath",
            description="The HTTP path for the Databricks SQL warehouse or cluster.",
        ),
    ] = None
    access_token: Annotated[
        str | None,
        Field(
            alias="accessToken",
            description="The personal access token for PAT authentication.",
        ),
    ] = None
    client_id: Annotated[
        str | None,
        Field(
            alias="clientId",
            description="The OAuth client ID for OAUTH_M2M authentication.",
        ),
    ] = None
    client_secret: Annotated[
        str | None,
        Field(
            alias="clientSecret",
            description="The OAuth client secret for OAUTH_M2M authentication.",
        ),
    ] = None


class ProblemProblemType(str, Enum):
    """The type of problem."""

    UNKNOWN = "UNKNOWN"
    ILLEGAL_ARGUMENT = "ILLEGAL_ARGUMENT"
    CANNOT_DELETE = "CANNOT_DELETE"
    GREATER_VALUE_REQUIRED = "GREATER_VALUE_REQUIRED"
    LESS_VALUE_REQUIRED = "LESS_VALUE_REQUIRED"
    NON_UNIQUE_VALUE = "NON_UNIQUE_VALUE"
    USER_EMAIL_ALREADY_EXISTS = "USER_EMAIL_ALREADY_EXISTS"
    INCORRECT_DATA_TYPE = "INCORRECT_DATA_TYPE"
    RATIO_CONVERSION_FAILED = "RATIO_CONVERSION_FAILED"
    RISK_SCORE_FILTER_CONVERSION_FAILED = "RISK_SCORE_FILTER_CONVERSION_FAILED"
    FILTER_CONVERSION_FAILED = "FILTER_CONVERSION_FAILED"
    POPULATION_CONVERSION_FAILED = "POPULATION_CONVERSION_FAILED"
    INSUFFICIENT_PERMISSION = "INSUFFICIENT_PERMISSION"
    ACCOUNT_GROUPING_NODES_CONTAIN_ERRORS = "ACCOUNT_GROUPING_NODES_CONTAIN_ERRORS"
    ACCOUNT_GROUPING_IN_USE_BY_LIBRARY = "ACCOUNT_GROUPING_IN_USE_BY_LIBRARY"
    INVALID_ACCOUNT_GROUPING_FILE = "INVALID_ACCOUNT_GROUPING_FILE"
    DELIVERY_FAILURE = "DELIVERY_FAILURE"
    INVALID_STATE = "INVALID_STATE"


class ProblemSeverity(str, Enum):
    """Indicates how severe the problem is."""

    WARNING = "WARNING"
    ERROR = "ERROR"


class Problem(BaseItem):
    problem_type: Annotated[
        ProblemProblemType | None,
        Field(alias="problemType", description="The type of problem."),
    ] = None
    severity: Annotated[
        ProblemSeverity | None,
        Field(description="Indicates how severe the problem is."),
    ] = None
    entity_type: Annotated[
        str | None,
        Field(
            alias="entityType",
            description="The type of entity impacted by the problem.",
        ),
    ] = None
    entity_id: Annotated[
        str | None,
        Field(
            alias="entityId",
            description="Identifies the entity impacted by the problem.",
        ),
    ] = None
    identifier: Annotated[
        str | None, Field(description="Identifies the field causing the problem.")
    ] = None
    values: Annotated[
        list[str] | None,
        Field(description="Identifies the values causing the problem."),
    ] = None
    reason: Annotated[
        str | None, Field(description="The reason(s) why the problem occurred.")
    ] = None
    suggested_values: Annotated[
        list[str] | None,
        Field(
            alias="suggestedValues",
            description="A suggested set of values to assist in resolving the problem.",
        ),
    ] = None
    problem_count: Annotated[
        int | None,
        Field(
            alias="problemCount",
            description="The total number of occurrences of this problem.",
        ),
    ] = None


class ApiCsvConfiguration(BaseItem):
    delimiter: Annotated[
        str | None, Field(description="The character used to separate entries.")
    ] = None
    quote: Annotated[
        str | None, Field(description="The character used to encapsulate an entry.")
    ] = None
    quote_escape: Annotated[
        str | None,
        Field(
            alias="quoteEscape",
            description="The character used to escape the quote character.",
        ),
    ] = None
    quote_escape_escape: Annotated[
        str | None,
        Field(
            alias="quoteEscapeEscape",
            description="The character used to escape the quote escape character.",
        ),
    ] = None


class ApiDataTableQuerySortOrderDirection(str, Enum):
    """How the column will be sorted."""

    ASC = "ASC"
    DESC = "DESC"


class ApiDataTableQuerySortOrder(BaseItem):
    field: Annotated[str | None, Field(description="The data table column.")] = None
    direction: Annotated[
        ApiDataTableQuerySortOrderDirection | None,
        Field(description="How the column will be sorted."),
    ] = None


class ShieldQueryTermOperatorShieldQueryTermOperatorEnum(str, Enum):
    FIELD_EQ = "$eq"
    FIELD_NE = "$ne"
    FIELD_GT = "$gt"
    FIELD_GTE = "$gte"
    FIELD_LT = "$lt"
    FIELD_LTE = "$lte"
    FIELD_CONTAINS = "$contains"
    FIELD_NCONTAINS = "$ncontains"
    FIELD_IN = "$in"
    FIELD_NIN = "$nin"
    FIELD_FLAGS = "$flags"
    FIELD_KEYWORD_PREFIX = "$keyword_prefix"
    FIELD_KEYWORD_PREFIX_NOT = "$keyword_prefix_not"
    FIELD_ISUBSTR = "$isubstr"
    FIELD_IPREFIX = "$iprefix"
    FIELD_NIPREFIX = "$niprefix"
    FIELD_BETWEEN = "$between"
    FIELD_NBETWEEN = "$nbetween"
    FIELD_AND = "$and"
    FIELD_OR = "$or"
    FIELD_POPULATION = "$population"
    FIELD_NOT_POPULATION = "$not_population"


ShieldQueryTermOperator = RootModel[
    ShieldQueryTermOperatorShieldQueryTermOperatorEnum | None
]


class ShieldQueryTerm(BaseItem):
    operator: ShieldQueryTermOperator | None = None


class ApiDataTablePage(BaseItem):
    content: list[dict[str, Any]] | None = None


class ApiDataTableQuerySortOrderReadDirection(str, Enum):
    """How the column will be sorted."""

    ASC = "ASC"
    DESC = "DESC"


class ApiDataTableQuerySortOrderRead(BaseItem):
    field: Annotated[str | None, Field(description="The data table column.")] = None
    direction: Annotated[
        ApiDataTableQuerySortOrderReadDirection | None,
        Field(description="How the column will be sorted."),
    ] = None


class ApiDataTableColumnReadType(str, Enum):
    """The type of data found in the column."""

    STRING = "STRING"
    DATE = "DATE"
    DATE_TIME = "DATE_TIME"
    BOOLEAN = "BOOLEAN"
    INT16 = "INT16"
    INT32 = "INT32"
    INT64 = "INT64"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"
    MONEY_100 = "MONEY_100"
    PERCENTAGE_FIXED_POINT = "PERCENTAGE_FIXED_POINT"
    ARRAY_STRINGS = "ARRAY_STRINGS"
    ARRAY_INT64 = "ARRAY_INT64"
    KEYWORD_SEARCH = "KEYWORD_SEARCH"
    OBJECTID = "OBJECTID"
    BOOLEAN_FLAGS = "BOOLEAN_FLAGS"
    MAP_SCALARS = "MAP_SCALARS"
    LEGACY_ACCOUNT_TAG_EFFECTS = "LEGACY_ACCOUNT_TAG_EFFECTS"
    JSONB = "JSONB"


class ApiDataTableColumnRead(BaseItem):
    original_name: Annotated[
        str | None,
        Field(
            alias="originalName",
            description="The original field name, derived from the source file, risk score name, or similar source.",
        ),
    ] = None
    field: Annotated[str | None, Field(description="The column name.")] = None
    mind_bridge_field: Annotated[
        str | None,
        Field(
            alias="mindBridgeField",
            description="The MindBridge field name that this column is mapped to.",
        ),
    ] = None
    type: Annotated[
        ApiDataTableColumnReadType | None,
        Field(description="The type of data found in the column."),
    ] = None
    nullable: Annotated[
        bool | None,
        Field(description="Indicates whether or not NULL values are allowed."),
    ] = None
    equality_search: Annotated[
        bool | None,
        Field(
            alias="equalitySearch",
            description="Indicates whether or not a search can be performed based on two equal operands.",
        ),
    ] = None
    range_search: Annotated[
        bool | None,
        Field(
            alias="rangeSearch",
            description="Indicates whether or not a search can be performed on a value-based comparison.",
        ),
    ] = None
    sortable: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the data table can be sorted by this column."
        ),
    ] = None
    contains_search: Annotated[
        bool | None,
        Field(
            alias="containsSearch",
            description="Indicates whether or not a value-based search can be performed.",
        ),
    ] = None
    keyword_search: Annotated[
        bool | None,
        Field(
            alias="keywordSearch",
            description="Indicates whether or not a keyword search can be performed.",
        ),
    ] = None
    case_insensitive_substring_search: Annotated[
        bool | None,
        Field(
            alias="caseInsensitiveSubstringSearch",
            description="Indicates whether or not a case insensitive search can be performed on a substring.",
        ),
    ] = None
    case_insensitive_prefix_search: Annotated[
        bool | None,
        Field(
            alias="caseInsensitivePrefixSearch",
            description="Indicates whether or not a case insensitive search can be performed on a prefix.",
        ),
    ] = None
    filter_only: Annotated[
        bool | None,
        Field(
            alias="filterOnly",
            description="Indicates whether a field can only be used as part of a filter.",
        ),
    ] = None
    typeahead_data_table_id: Annotated[
        str | None,
        Field(
            alias="typeaheadDataTableId",
            description="The ID of the typeahead table that this column references.",
        ),
    ] = None


class ApiDataTableRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="Identifies the associated analysis."),
    ] = None
    analysis_result_id: Annotated[
        str | None,
        Field(
            alias="analysisResultId",
            description="Identifies the associated analysis results.",
        ),
    ] = None
    logical_name: Annotated[
        str | None,
        Field(alias="logicalName", description="The name of the data table."),
    ] = None
    type: Annotated[str | None, Field(description="The type of data table.")] = None
    columns: Annotated[
        list[ApiDataTableColumnRead] | None,
        Field(description="Details about the data table columns."),
    ] = None


class ApiConnectionCreateType(str, Enum):
    """The type of external connection."""

    DATABRICKS = "DATABRICKS"
    MINDBRIDGE_DATA_TABLES = "MINDBRIDGE_DATA_TABLES"


class ApiConnectionCreate(BaseItem):
    type: Annotated[
        ApiConnectionCreateType | None,
        Field(description="The type of external connection."),
    ] = None


class ApiConnectionReadType(str, Enum):
    """The type of external connection."""

    DATABRICKS = "DATABRICKS"
    MINDBRIDGE_DATA_TABLES = "MINDBRIDGE_DATA_TABLES"


class ApiConnectionRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    type: Annotated[
        ApiConnectionReadType | None,
        Field(description="The type of external connection."),
    ] = None


class ApiTabularSchemaColumnCreateColumnType(str, Enum):
    """The data type of the column."""

    STRING = "STRING"
    DATE = "DATE"
    DATE_TIME = "DATE_TIME"
    BOOLEAN = "BOOLEAN"
    INT16 = "INT16"
    INT32 = "INT32"
    INT64 = "INT64"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"
    MONEY_100 = "MONEY_100"
    PERCENTAGE_FIXED_POINT = "PERCENTAGE_FIXED_POINT"
    ARRAY_STRINGS = "ARRAY_STRINGS"
    ARRAY_INT64 = "ARRAY_INT64"
    KEYWORD_SEARCH = "KEYWORD_SEARCH"
    OBJECTID = "OBJECTID"
    BOOLEAN_FLAGS = "BOOLEAN_FLAGS"
    MAP_SCALARS = "MAP_SCALARS"
    LEGACY_ACCOUNT_TAG_EFFECTS = "LEGACY_ACCOUNT_TAG_EFFECTS"
    JSONB = "JSONB"


class ApiTabularSchemaColumnCreate(BaseItem):
    name: Annotated[str | None, Field(description="The name of the column.")] = None
    column_type: Annotated[
        ApiTabularSchemaColumnCreateColumnType | None,
        Field(alias="columnType", description="The data type of the column."),
    ] = None
    nullable: Annotated[
        bool | None, Field(description="Whether the column allows null values.")
    ] = None


class ApiTabularSchemaCreate(BaseItem):
    columns: Annotated[
        list[ApiTabularSchemaColumnCreate] | None,
        Field(description="The list of column definitions for the table."),
    ] = None


class ApiConnectionTestResultRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection that was tested.",
        ),
    ] = None
    message: Annotated[
        str | None,
        Field(description="A message describing the outcome of the connection test."),
    ] = None


class ApiTabularSchemaColumnReadColumnType(str, Enum):
    """The data type of the column."""

    STRING = "STRING"
    DATE = "DATE"
    DATE_TIME = "DATE_TIME"
    BOOLEAN = "BOOLEAN"
    INT16 = "INT16"
    INT32 = "INT32"
    INT64 = "INT64"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"
    MONEY_100 = "MONEY_100"
    PERCENTAGE_FIXED_POINT = "PERCENTAGE_FIXED_POINT"
    ARRAY_STRINGS = "ARRAY_STRINGS"
    ARRAY_INT64 = "ARRAY_INT64"
    KEYWORD_SEARCH = "KEYWORD_SEARCH"
    OBJECTID = "OBJECTID"
    BOOLEAN_FLAGS = "BOOLEAN_FLAGS"
    MAP_SCALARS = "MAP_SCALARS"
    LEGACY_ACCOUNT_TAG_EFFECTS = "LEGACY_ACCOUNT_TAG_EFFECTS"
    JSONB = "JSONB"


class ApiTabularSchemaColumnRead(BaseItem):
    name: Annotated[str | None, Field(description="The name of the column.")] = None
    column_type: Annotated[
        ApiTabularSchemaColumnReadColumnType | None,
        Field(alias="columnType", description="The data type of the column."),
    ] = None
    nullable: Annotated[
        bool | None, Field(description="Whether the column allows null values.")
    ] = None


class ApiTabularSchemaRead(BaseItem):
    columns: Annotated[
        list[ApiTabularSchemaColumnRead] | None,
        Field(description="The list of column definitions for the table."),
    ] = None


class ApiConnectionTablesResultRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection that this tables result belongs to.",
        ),
    ] = None
    table_count: Annotated[
        int | None,
        Field(
            alias="tableCount",
            description="The total number of tables discovered from the connection.",
        ),
    ] = None


class ApiConnectionDataSourceCreate(BaseItem):
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection this data source belongs to.",
        ),
    ] = None
    table_id: Annotated[
        str | None,
        Field(
            alias="tableId",
            description="The identifier of the table within the external connection.",
        ),
    ] = None
    schema_: Annotated[
        ApiTabularSchemaCreate | None,
        Field(
            alias="schema",
            description="The schema describing the columns of the table.",
        ),
    ] = None


class ApiConnectionDataSourceRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection this data source belongs to.",
        ),
    ] = None
    table_id: Annotated[
        str | None,
        Field(
            alias="tableId",
            description="The identifier of the table within the external connection.",
        ),
    ] = None
    schema_: Annotated[
        ApiTabularSchemaRead | None,
        Field(
            alias="schema",
            description="The schema describing the columns of the table.",
        ),
    ] = None


class ApiDataSourceDataRequestCreate(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="Identifies the engagement that the resulting Data Table will be associated with.",
        ),
    ] = None
    filter: Annotated[
        ShieldQueryTermCreate | None,
        Field(
            description="Optional filter to apply to the data retrieval. If not set, all rows are returned unfiltered."
        ),
    ] = None
    limit: Annotated[
        int | None,
        Field(
            description="Maximum number of rows to return. If not set, all matching rows are returned.",
            ge=0,
        ),
    ] = None
    offset: Annotated[
        int | None,
        Field(
            description="Number of rows to skip before returning results. If not set, results start from the first row.",
            ge=0,
        ),
    ] = None


class ApiChunkedFileCreate(BaseItem):
    name: Annotated[str | None, Field(description="The name of the chunked file.")] = (
        None
    )
    size: Annotated[
        int | None, Field(description="The size of the chunked file.", ge=0)
    ] = None


class ApiChunkedFilePartRead(BaseItem):
    offset: Annotated[
        int | None,
        Field(
            description="Indicates the start position of the file part in the chunked file.",
            ge=0,
        ),
    ] = None
    size: Annotated[
        int | None, Field(description="The size of the file part.", ge=0)
    ] = None


class ApiChunkedFileRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    name: Annotated[str | None, Field(description="The name of the chunked file.")] = (
        None
    )
    size: Annotated[
        int | None, Field(description="The size of the chunked file.", ge=0)
    ] = None
    chunked_file_parts: Annotated[
        list[ApiChunkedFilePartRead] | None,
        Field(
            alias="chunkedFileParts",
            description="The offset and size of the chunked file parts.",
        ),
    ] = None


class ApiChunkedFilePart(BaseItem):
    offset: Annotated[
        int | None,
        Field(
            description="Indicates the start position of the file part in the chunked file.",
            ge=0,
        ),
    ] = None
    size: Annotated[
        int | None, Field(description="The size of the file part.", ge=0)
    ] = None


class ApiApiTokenCreatePermission(str, Enum):
    API_ORGANIZATIONS_READ = "api.organizations.read"
    API_ORGANIZATIONS_WRITE = "api.organizations.write"
    API_ORGANIZATIONS_DELETE = "api.organizations.delete"
    API_ENGAGEMENTS_READ = "api.engagements.read"
    API_ENGAGEMENTS_WRITE = "api.engagements.write"
    API_ENGAGEMENTS_DELETE = "api.engagements.delete"
    API_ANALYSES_READ = "api.analyses.read"
    API_ANALYSES_WRITE = "api.analyses.write"
    API_ANALYSES_DELETE = "api.analyses.delete"
    API_ANALYSES_RUN = "api.analyses.run"
    API_ANALYSIS_SOURCES_READ = "api.analysis-sources.read"
    API_ANALYSIS_SOURCES_WRITE = "api.analysis-sources.write"
    API_ANALYSIS_SOURCES_DELETE = "api.analysis-sources.delete"
    API_FILE_MANAGER_READ = "api.file-manager.read"
    API_FILE_MANAGER_WRITE = "api.file-manager.write"
    API_FILE_MANAGER_DELETE = "api.file-manager.delete"
    API_REPORTING_PERIOD_CONFIG_READ = "api.reporting-period-config.read"
    API_REPORTING_PERIOD_CONFIG_WRITE = "api.reporting-period-config.write"
    API_REPORTING_PERIOD_CONFIG_DELETE = "api.reporting-period-config.delete"
    API_LIBRARIES_READ = "api.libraries.read"
    API_LIBRARIES_WRITE = "api.libraries.write"
    API_LIBRARIES_DELETE = "api.libraries.delete"
    API_ACCOUNT_GROUPINGS_READ = "api.account-groupings.read"
    API_ACCOUNT_GROUPINGS_WRITE = "api.account-groupings.write"
    API_ACCOUNT_GROUPINGS_DELETE = "api.account-groupings.delete"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_READ = "api.engagement-account-groupings.read"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_WRITE = "api.engagement-account-groupings.write"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_DELETE = "api.engagement-account-groupings.delete"
    API_USERS_READ = "api.users.read"
    API_USERS_WRITE = "api.users.write"
    API_USERS_DELETE = "api.users.delete"
    API_DATA_TABLES_READ = "api.data-tables.read"
    API_API_TOKENS_READ = "api.api-tokens.read"
    API_API_TOKENS_WRITE = "api.api-tokens.write"
    API_API_TOKENS_DELETE = "api.api-tokens.delete"
    API_TASKS_READ = "api.tasks.read"
    API_TASKS_WRITE = "api.tasks.write"
    API_TASKS_DELETE = "api.tasks.delete"
    API_ADMIN_REPORTS_RUN = "api.admin-reports.run"
    API_ANALYSIS_TYPES_READ = "api.analysis-types.read"
    API_ANALYSIS_SOURCE_TYPES_READ = "api.analysis-source-types.read"
    API_ANALYSIS_TYPE_CONFIGURATION_READ = "api.analysis-type-configuration.read"
    API_ANALYSIS_TYPE_CONFIGURATION_WRITE = "api.analysis-type-configuration.write"
    API_ANALYSIS_TYPE_CONFIGURATION_DELETE = "api.analysis-type-configuration.delete"
    API_RISK_RANGES_READ = "api.risk-ranges.read"
    API_RISK_RANGES_WRITE = "api.risk-ranges.write"
    API_RISK_RANGES_DELETE = "api.risk-ranges.delete"
    API_FILTERS_READ = "api.filters.read"
    API_FILTERS_WRITE = "api.filters.write"
    API_FILTERS_DELETE = "api.filters.delete"
    API_FILE_INFOS_READ = "api.file-infos.read"
    API_WEBHOOKS_READ = "api.webhooks.read"
    API_WEBHOOKS_WRITE = "api.webhooks.write"
    API_WEBHOOKS_DELETE = "api.webhooks.delete"
    API_CONNECTIONS_READ = "api.connections.read"
    API_CONNECTIONS_WRITE = "api.connections.write"
    API_CONNECTIONS_DELETE = "api.connections.delete"
    API_CONNECTION_DATA_SOURCES_READ = "api.connection-data-sources.read"
    API_CONNECTION_DATA_SOURCES_WRITE = "api.connection-data-sources.write"
    API_CONNECTION_DATA_SOURCES_DELETE = "api.connection-data-sources.delete"
    SCIM_USER_READ = "scim.user.read"
    SCIM_USER_WRITE = "scim.user.write"
    SCIM_USER_DELETE = "scim.user.delete"
    SCIM_USER_SCHEMA = "scim.user.schema"


class ApiApiTokenCreate(BaseItem):
    name: Annotated[
        str | None,
        Field(
            description="The token record's name. This will also be used as the API Token User's name."
        ),
    ] = None
    expiry: Annotated[
        AwareDatetime | None,
        Field(description="The day on which the API token expires."),
    ] = None
    allowed_addresses: Annotated[
        list[str] | None,
        Field(
            alias="allowedAddresses",
            description="Indicates the set of addresses that are allowed to use this token. If empty, any address may use it.",
        ),
    ] = None
    permissions: Annotated[
        list[ApiApiTokenCreatePermission] | None,
        Field(
            description="The set of permissions that inform which endpoints this token is authorized to access."
        ),
    ] = None


class CreateApiTokenResponseReadPermission(str, Enum):
    API_ORGANIZATIONS_READ = "api.organizations.read"
    API_ORGANIZATIONS_WRITE = "api.organizations.write"
    API_ORGANIZATIONS_DELETE = "api.organizations.delete"
    API_ENGAGEMENTS_READ = "api.engagements.read"
    API_ENGAGEMENTS_WRITE = "api.engagements.write"
    API_ENGAGEMENTS_DELETE = "api.engagements.delete"
    API_ANALYSES_READ = "api.analyses.read"
    API_ANALYSES_WRITE = "api.analyses.write"
    API_ANALYSES_DELETE = "api.analyses.delete"
    API_ANALYSES_RUN = "api.analyses.run"
    API_ANALYSIS_SOURCES_READ = "api.analysis-sources.read"
    API_ANALYSIS_SOURCES_WRITE = "api.analysis-sources.write"
    API_ANALYSIS_SOURCES_DELETE = "api.analysis-sources.delete"
    API_FILE_MANAGER_READ = "api.file-manager.read"
    API_FILE_MANAGER_WRITE = "api.file-manager.write"
    API_FILE_MANAGER_DELETE = "api.file-manager.delete"
    API_REPORTING_PERIOD_CONFIG_READ = "api.reporting-period-config.read"
    API_REPORTING_PERIOD_CONFIG_WRITE = "api.reporting-period-config.write"
    API_REPORTING_PERIOD_CONFIG_DELETE = "api.reporting-period-config.delete"
    API_LIBRARIES_READ = "api.libraries.read"
    API_LIBRARIES_WRITE = "api.libraries.write"
    API_LIBRARIES_DELETE = "api.libraries.delete"
    API_ACCOUNT_GROUPINGS_READ = "api.account-groupings.read"
    API_ACCOUNT_GROUPINGS_WRITE = "api.account-groupings.write"
    API_ACCOUNT_GROUPINGS_DELETE = "api.account-groupings.delete"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_READ = "api.engagement-account-groupings.read"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_WRITE = "api.engagement-account-groupings.write"
    API_ENGAGEMENT_ACCOUNT_GROUPINGS_DELETE = "api.engagement-account-groupings.delete"
    API_USERS_READ = "api.users.read"
    API_USERS_WRITE = "api.users.write"
    API_USERS_DELETE = "api.users.delete"
    API_DATA_TABLES_READ = "api.data-tables.read"
    API_API_TOKENS_READ = "api.api-tokens.read"
    API_API_TOKENS_WRITE = "api.api-tokens.write"
    API_API_TOKENS_DELETE = "api.api-tokens.delete"
    API_TASKS_READ = "api.tasks.read"
    API_TASKS_WRITE = "api.tasks.write"
    API_TASKS_DELETE = "api.tasks.delete"
    API_ADMIN_REPORTS_RUN = "api.admin-reports.run"
    API_ANALYSIS_TYPES_READ = "api.analysis-types.read"
    API_ANALYSIS_SOURCE_TYPES_READ = "api.analysis-source-types.read"
    API_ANALYSIS_TYPE_CONFIGURATION_READ = "api.analysis-type-configuration.read"
    API_ANALYSIS_TYPE_CONFIGURATION_WRITE = "api.analysis-type-configuration.write"
    API_ANALYSIS_TYPE_CONFIGURATION_DELETE = "api.analysis-type-configuration.delete"
    API_RISK_RANGES_READ = "api.risk-ranges.read"
    API_RISK_RANGES_WRITE = "api.risk-ranges.write"
    API_RISK_RANGES_DELETE = "api.risk-ranges.delete"
    API_FILTERS_READ = "api.filters.read"
    API_FILTERS_WRITE = "api.filters.write"
    API_FILTERS_DELETE = "api.filters.delete"
    API_FILE_INFOS_READ = "api.file-infos.read"
    API_WEBHOOKS_READ = "api.webhooks.read"
    API_WEBHOOKS_WRITE = "api.webhooks.write"
    API_WEBHOOKS_DELETE = "api.webhooks.delete"
    API_CONNECTIONS_READ = "api.connections.read"
    API_CONNECTIONS_WRITE = "api.connections.write"
    API_CONNECTIONS_DELETE = "api.connections.delete"
    API_CONNECTION_DATA_SOURCES_READ = "api.connection-data-sources.read"
    API_CONNECTION_DATA_SOURCES_WRITE = "api.connection-data-sources.write"
    API_CONNECTION_DATA_SOURCES_DELETE = "api.connection-data-sources.delete"
    SCIM_USER_READ = "scim.user.read"
    SCIM_USER_WRITE = "scim.user.write"
    SCIM_USER_DELETE = "scim.user.delete"
    SCIM_USER_SCHEMA = "scim.user.schema"


class CreateApiTokenResponseRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    user_id: Annotated[
        str | None,
        Field(
            alias="userId",
            description="Identifies the API Token User associated with this token.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(
            description="The token record's name. This will also be used as the API Token User's name."
        ),
    ] = None
    partial_token: Annotated[
        str | None,
        Field(
            alias="partialToken",
            description="A partial representation of the API token.",
        ),
    ] = None
    expiry: Annotated[
        AwareDatetime | None,
        Field(description="The day on which the API token expires."),
    ] = None
    allowed_addresses: Annotated[
        list[str] | None,
        Field(
            alias="allowedAddresses",
            description="Indicates the set of addresses that are allowed to use this token. If empty, any address may use it.",
        ),
    ] = None
    permissions: Annotated[
        list[CreateApiTokenResponseReadPermission] | None,
        Field(
            description="The set of permissions that inform which endpoints this token is authorized to access."
        ),
    ] = None
    token: Annotated[
        str | None,
        Field(
            description="The API token.\n\n**Note:** The security of the API token is paramount. If compromised, contact your **App Admin** immediately."
        ),
    ] = None


class ApiSourceConfigurationReadSourceScope(str, Enum):
    """Indicates whether the source configuration applies to the current period, all of the prior periods, or the entire analysis.

    **Note**: Sources with an `ANALYSIS` scope should not provide an `analysisPeriodId`.
    """

    CURRENT_PERIOD = "CURRENT_PERIOD"
    PRIOR_PERIOD = "PRIOR_PERIOD"
    ANALYSIS = "ANALYSIS"


class ApiSourceConfigurationRead(BaseItem):
    source_type_id: Annotated[
        str | None,
        Field(
            alias="sourceTypeId",
            description="The source type ID selected as part of this configuration.",
        ),
    ] = None
    source_scope: Annotated[
        ApiSourceConfigurationReadSourceScope | None,
        Field(
            alias="sourceScope",
            description="Indicates whether the source configuration applies to the current period, all of the prior periods, or the entire analysis.\n\n**Note**: Sources with an `ANALYSIS` scope should not provide an `analysisPeriodId`.",
        ),
    ] = None
    required: Annotated[
        bool | None,
        Field(
            description="When `true`, the analysis cannot be run until at least one analysis source with this source type in this source scope is present."
        ),
    ] = None
    post_analysis: Annotated[
        bool | None,
        Field(
            alias="postAnalysis",
            description="When `true`, this source configuration will be enabled after an analysis is run (not before).",
        ),
    ] = None
    interim_only: Annotated[
        bool | None,
        Field(
            alias="interimOnly",
            description="When `true`, this source configuration only applies when the interim time frame is used (i.e., it has not been converted for use with a full time frame).",
        ),
    ] = None
    disable_for_interim: Annotated[
        bool | None,
        Field(
            alias="disableForInterim",
            description="When `true` and the interim time frame is used (i.e., it has not been converted for use with a full time frame), new analysis sources of this source type and source scope cannot be added.",
        ),
    ] = None
    allow_multiple: Annotated[
        bool | None,
        Field(
            alias="allowMultiple",
            description="When `true`, multiple versions of this analysis source type may be imported using this source scope.",
        ),
    ] = None
    allow_multiple_for_periodic: Annotated[
        bool | None,
        Field(
            alias="allowMultipleForPeriodic",
            description="When `true` and the periodic time frame is used, multiple versions of this analysis source type may be imported using this source scope.",
        ),
    ] = None
    alternative_required_source_types: Annotated[
        list[str] | None,
        Field(
            alias="alternativeRequiredSourceTypes",
            description="A list of alternative analysis source types. If one of the alternatives is present for this source scope, then the `required` constraint is considered satisfied.",
        ),
    ] = None
    tracks_additional_data_entries: Annotated[
        bool | None,
        Field(
            alias="tracksAdditionalDataEntries",
            description="When `true`, the `additionalDataColumnField` field is required upon importing an analysis source type.",
        ),
    ] = None


class ApiAnalysisSourceCreateTargetWorkflowState(str, Enum):
    """The state that the current workflow will advance to."""

    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    STARTED = "STARTED"
    DETECTING_FORMAT = "DETECTING_FORMAT"
    ANALYZING_COLUMNS = "ANALYZING_COLUMNS"
    CHECKING_INTEGRITY = "CHECKING_INTEGRITY"
    SCANNING_TRANSACTION_COMBINATIONS = "SCANNING_TRANSACTION_COMBINATIONS"
    PARSING = "PARSING"
    PARSING_ICEBERG = "PARSING_ICEBERG"
    ANALYZING_EFFECTIVE_DATE_METRICS = "ANALYZING_EFFECTIVE_DATE_METRICS"
    FORMAT_DETECTION_COMPLETED = "FORMAT_DETECTION_COMPLETED"
    COLUMN_MAPPINGS_CONFIRMED = "COLUMN_MAPPINGS_CONFIRMED"
    SETTINGS_CONFIRMED = "SETTINGS_CONFIRMED"
    PREPARING_ICEBERG = "PREPARING_ICEBERG"
    ANALYSIS_PERIOD_SELECTED = "ANALYSIS_PERIOD_SELECTED"
    FUNDS_REVIEWED = "FUNDS_REVIEWED"
    RUNNING = "RUNNING"
    UNPACK_COMPLETE = "UNPACK_COMPLETE"
    UPLOADED = "UPLOADED"
    FORMAT_DETECTED = "FORMAT_DETECTED"
    COLUMNS_ANALYZED = "COLUMNS_ANALYZED"
    INTEGRITY_CHECKED = "INTEGRITY_CHECKED"
    PARSED = "PARSED"
    AUTHENTICATED = "AUTHENTICATED"
    CONFIGURED = "CONFIGURED"
    EFFECTIVE_DATE_METRICS_ANALYZED = "EFFECTIVE_DATE_METRICS_ANALYZED"
    DATA_VALIDATION_CONFIRMED = "DATA_VALIDATION_CONFIRMED"


class ApiProposedAmbiguousColumnResolutionCreate(BaseItem):
    position: Annotated[
        int | None,
        Field(
            description="The position of the column with the proposed resolution.", ge=0
        ),
    ] = None
    selected_format: Annotated[
        str | None,
        Field(
            alias="selectedFormat",
            description="The selected format of the proposed resolution.",
        ),
    ] = None


class ApiProposedColumnMappingCreate(BaseItem):
    column_position: Annotated[
        int | None,
        Field(
            alias="columnPosition",
            description="The position of the proposed column mapping in the original input file.",
        ),
    ] = None
    virtual_column_index: Annotated[
        int | None,
        Field(
            alias="virtualColumnIndex",
            description="The position of the proposed virtual columns within the `proposedVirtualColumns` list.",
        ),
    ] = None
    mindbridge_field: Annotated[
        str | None,
        Field(
            alias="mindbridgeField",
            description="The MindBridge field that the data column should be mapped to.",
        ),
    ] = None
    additional_column_name: Annotated[
        str | None,
        Field(
            alias="additionalColumnName",
            description="Proposed additional columns of data to be added to the analysis.",
        ),
    ] = None


class ApiProposedVirtualColumnCreateType(str, Enum):
    """The type of proposed virtual column."""

    DUPLICATE = "DUPLICATE"
    SPLIT_BY_POSITION = "SPLIT_BY_POSITION"
    SPLIT_BY_DELIMITER = "SPLIT_BY_DELIMITER"
    JOIN = "JOIN"


class ApiProposedVirtualColumnCreate(BaseItem):
    name: Annotated[
        str | None, Field(description="The name of the proposed virtual column.")
    ] = None
    type: Annotated[
        ApiProposedVirtualColumnCreateType | None,
        Field(description="The type of proposed virtual column."),
    ] = None


class ApiTransactionIdSelectionCreateType(str, Enum):
    """The type used when selecting a transaction ID."""

    COMBINATION = "COMBINATION"
    RUNNING_TOTAL = "RUNNING_TOTAL"


class ApiTransactionIdSelectionCreate(BaseItem):
    column_selection: Annotated[
        list[int] | None,
        Field(
            alias="columnSelection",
            description="The columns included when selecting a transaction ID.",
        ),
    ] = None
    virtual_column_selection: Annotated[
        list[int] | None,
        Field(
            alias="virtualColumnSelection",
            description="The virtual columns included when selecting a transaction ID.",
        ),
    ] = None
    type: Annotated[
        ApiTransactionIdSelectionCreateType | None,
        Field(description="The type used when selecting a transaction ID."),
    ] = None
    apply_smart_splitter: Annotated[
        bool | None,
        Field(
            alias="applySmartSplitter",
            description="Indicates whether or not the Smart Splitter was run when selecting a transaction ID.",
        ),
    ] = None


class ApiAmbiguousColumnRead(BaseItem):
    position: Annotated[
        int | None, Field(description="The position of the column with the resolution.")
    ] = None
    ambiguous_formats: Annotated[
        list[str] | None,
        Field(
            alias="ambiguousFormats",
            description="A list of ambiguous formats detected.",
        ),
    ] = None
    selected_format: Annotated[
        str | None,
        Field(
            alias="selectedFormat",
            description="The data format to be used in case of ambiguity.",
        ),
    ] = None


class ApiAnalysisSourceReadWorkflowState(str, Enum):
    """The current state of the workflow."""

    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    STARTED = "STARTED"
    DETECTING_FORMAT = "DETECTING_FORMAT"
    ANALYZING_COLUMNS = "ANALYZING_COLUMNS"
    CHECKING_INTEGRITY = "CHECKING_INTEGRITY"
    SCANNING_TRANSACTION_COMBINATIONS = "SCANNING_TRANSACTION_COMBINATIONS"
    PARSING = "PARSING"
    PARSING_ICEBERG = "PARSING_ICEBERG"
    ANALYZING_EFFECTIVE_DATE_METRICS = "ANALYZING_EFFECTIVE_DATE_METRICS"
    FORMAT_DETECTION_COMPLETED = "FORMAT_DETECTION_COMPLETED"
    COLUMN_MAPPINGS_CONFIRMED = "COLUMN_MAPPINGS_CONFIRMED"
    SETTINGS_CONFIRMED = "SETTINGS_CONFIRMED"
    PREPARING_ICEBERG = "PREPARING_ICEBERG"
    ANALYSIS_PERIOD_SELECTED = "ANALYSIS_PERIOD_SELECTED"
    FUNDS_REVIEWED = "FUNDS_REVIEWED"
    RUNNING = "RUNNING"
    UNPACK_COMPLETE = "UNPACK_COMPLETE"
    UPLOADED = "UPLOADED"
    FORMAT_DETECTED = "FORMAT_DETECTED"
    COLUMNS_ANALYZED = "COLUMNS_ANALYZED"
    INTEGRITY_CHECKED = "INTEGRITY_CHECKED"
    PARSED = "PARSED"
    AUTHENTICATED = "AUTHENTICATED"
    CONFIGURED = "CONFIGURED"
    EFFECTIVE_DATE_METRICS_ANALYZED = "EFFECTIVE_DATE_METRICS_ANALYZED"
    DATA_VALIDATION_CONFIRMED = "DATA_VALIDATION_CONFIRMED"


class ApiAnalysisSourceReadTargetWorkflowState(str, Enum):
    """The state that the current workflow will advance to."""

    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    STARTED = "STARTED"
    DETECTING_FORMAT = "DETECTING_FORMAT"
    ANALYZING_COLUMNS = "ANALYZING_COLUMNS"
    CHECKING_INTEGRITY = "CHECKING_INTEGRITY"
    SCANNING_TRANSACTION_COMBINATIONS = "SCANNING_TRANSACTION_COMBINATIONS"
    PARSING = "PARSING"
    PARSING_ICEBERG = "PARSING_ICEBERG"
    ANALYZING_EFFECTIVE_DATE_METRICS = "ANALYZING_EFFECTIVE_DATE_METRICS"
    FORMAT_DETECTION_COMPLETED = "FORMAT_DETECTION_COMPLETED"
    COLUMN_MAPPINGS_CONFIRMED = "COLUMN_MAPPINGS_CONFIRMED"
    SETTINGS_CONFIRMED = "SETTINGS_CONFIRMED"
    PREPARING_ICEBERG = "PREPARING_ICEBERG"
    ANALYSIS_PERIOD_SELECTED = "ANALYSIS_PERIOD_SELECTED"
    FUNDS_REVIEWED = "FUNDS_REVIEWED"
    RUNNING = "RUNNING"
    UNPACK_COMPLETE = "UNPACK_COMPLETE"
    UPLOADED = "UPLOADED"
    FORMAT_DETECTED = "FORMAT_DETECTED"
    COLUMNS_ANALYZED = "COLUMNS_ANALYZED"
    INTEGRITY_CHECKED = "INTEGRITY_CHECKED"
    PARSED = "PARSED"
    AUTHENTICATED = "AUTHENTICATED"
    CONFIGURED = "CONFIGURED"
    EFFECTIVE_DATE_METRICS_ANALYZED = "EFFECTIVE_DATE_METRICS_ANALYZED"
    DATA_VALIDATION_CONFIRMED = "DATA_VALIDATION_CONFIRMED"


class ApiAnalysisSourceReadDetectedFormat(str, Enum):
    """The data format that MindBridge detected."""

    QUICKBOOKS_JOURNAL = "QUICKBOOKS_JOURNAL"
    QUICKBOOKS_JOURNAL_2024 = "QUICKBOOKS_JOURNAL_2024"
    QUICKBOOKS_TRANSACTION_DETAIL_BY_ACCOUNT = (
        "QUICKBOOKS_TRANSACTION_DETAIL_BY_ACCOUNT"
    )
    SAGE50_LEDGER = "SAGE50_LEDGER"
    SAGE50_TRANSACTIONS = "SAGE50_TRANSACTIONS"
    CCH_ACCOUNT_LIST = "CCH_ACCOUNT_LIST"
    MS_DYNAMICS_JOURNAL = "MS_DYNAMICS_JOURNAL"
    SAGE50_UK = "SAGE50_UK"


class ApiColumnMappingReadMappingType(str, Enum):
    """The method used to map the column."""

    AUTO = "AUTO"
    NOT_MAPPED = "NOT_MAPPED"
    MANUAL = "MANUAL"


class ApiColumnMappingRead(BaseItem):
    position: Annotated[
        int | None, Field(description="The position of the column mapping.")
    ] = None
    field: Annotated[str | None, Field(description="The column name.")] = None
    mindbridge_field: Annotated[
        str | None,
        Field(
            alias="mindbridgeField",
            description="The MindBridge field that the data column was mapped to.",
        ),
    ] = None
    mapping_type: Annotated[
        ApiColumnMappingReadMappingType | None,
        Field(alias="mappingType", description="The method used to map the column."),
    ] = None
    additional_column_name: Annotated[
        str | None,
        Field(
            alias="additionalColumnName",
            description="Additional columns of data that were added to the analysis.",
        ),
    ] = None


class ApiMessageRead(BaseItem):
    code: Annotated[str | None, Field(description="Identifies the message type.")] = (
        None
    )
    default_message: Annotated[
        str | None,
        Field(
            alias="defaultMessage",
            description="The message as it appears in MindBridge.",
        ),
    ] = None


class ApiProposedAmbiguousColumnResolutionRead(BaseItem):
    position: Annotated[
        int | None,
        Field(
            description="The position of the column with the proposed resolution.", ge=0
        ),
    ] = None
    selected_format: Annotated[
        str | None,
        Field(
            alias="selectedFormat",
            description="The selected format of the proposed resolution.",
        ),
    ] = None


class ApiProposedColumnMappingRead(BaseItem):
    column_position: Annotated[
        int | None,
        Field(
            alias="columnPosition",
            description="The position of the proposed column mapping in the original input file.",
        ),
    ] = None
    virtual_column_index: Annotated[
        int | None,
        Field(
            alias="virtualColumnIndex",
            description="The position of the proposed virtual columns within the `proposedVirtualColumns` list.",
        ),
    ] = None
    mindbridge_field: Annotated[
        str | None,
        Field(
            alias="mindbridgeField",
            description="The MindBridge field that the data column should be mapped to.",
        ),
    ] = None
    additional_column_name: Annotated[
        str | None,
        Field(
            alias="additionalColumnName",
            description="Proposed additional columns of data to be added to the analysis.",
        ),
    ] = None


class ApiProposedVirtualColumnReadType(str, Enum):
    """The type of proposed virtual column."""

    DUPLICATE = "DUPLICATE"
    SPLIT_BY_POSITION = "SPLIT_BY_POSITION"
    SPLIT_BY_DELIMITER = "SPLIT_BY_DELIMITER"
    JOIN = "JOIN"


class ApiProposedVirtualColumnRead(BaseItem):
    name: Annotated[
        str | None, Field(description="The name of the proposed virtual column.")
    ] = None
    type: Annotated[
        ApiProposedVirtualColumnReadType | None,
        Field(description="The type of proposed virtual column."),
    ] = None


class ApiTransactionIdSelectionReadType(str, Enum):
    """The type used when selecting a transaction ID."""

    COMBINATION = "COMBINATION"
    RUNNING_TOTAL = "RUNNING_TOTAL"


class ApiTransactionIdSelectionRead(BaseItem):
    column_selection: Annotated[
        list[int] | None,
        Field(
            alias="columnSelection",
            description="The columns included when selecting a transaction ID.",
        ),
    ] = None
    virtual_column_selection: Annotated[
        list[int] | None,
        Field(
            alias="virtualColumnSelection",
            description="The virtual columns included when selecting a transaction ID.",
        ),
    ] = None
    type: Annotated[
        ApiTransactionIdSelectionReadType | None,
        Field(description="The type used when selecting a transaction ID."),
    ] = None
    apply_smart_splitter: Annotated[
        bool | None,
        Field(
            alias="applySmartSplitter",
            description="Indicates whether or not the Smart Splitter was run when selecting a transaction ID.",
        ),
    ] = None


class ApiVirtualColumnReadType(str, Enum):
    """The type of virtual column."""

    DUPLICATE = "DUPLICATE"
    SPLIT_BY_POSITION = "SPLIT_BY_POSITION"
    SPLIT_BY_DELIMITER = "SPLIT_BY_DELIMITER"
    JOIN = "JOIN"


class ApiVirtualColumnRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    index: Annotated[
        int | None, Field(description="The position of the virtual column.")
    ] = None
    name: Annotated[
        str | None, Field(description="The name of the virtual column.")
    ] = None
    type: Annotated[
        ApiVirtualColumnReadType | None,
        Field(description="The type of virtual column."),
    ] = None


class ApiAnalysisSourceTypeReadFeature(str, Enum):
    FORMAT_DETECTION = "FORMAT_DETECTION"
    DATA_VALIDATION = "DATA_VALIDATION"
    COLUMN_MAPPING = "COLUMN_MAPPING"
    EFFECTIVE_DATE_METRICS = "EFFECTIVE_DATE_METRICS"
    TRANSACTION_ID_SELECTION = "TRANSACTION_ID_SELECTION"
    PARSE = "PARSE"
    CONFIRM_SETTINGS = "CONFIRM_SETTINGS"
    REVIEW_FUNDS = "REVIEW_FUNDS"


class ApiColumnDefinitionReadType(str, Enum):
    """The type of data this column accepts."""

    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    UNKNOWN = "UNKNOWN"
    FLOAT64 = "FLOAT64"


class ApiColumnDefinitionRead(BaseItem):
    mindbridge_field_name: Annotated[
        str | None,
        Field(
            alias="mindbridgeFieldName",
            description="The internal name of the analysis source type's column.",
        ),
    ] = None
    mindbridge_field_name_for_non_mac_groupings: Annotated[
        str | None,
        Field(
            alias="mindbridgeFieldNameForNonMacGroupings",
            description="The alternative column name when a non-MAC based account grouping is used.",
        ),
    ] = None
    type: Annotated[
        ApiColumnDefinitionReadType | None,
        Field(description="The type of data this column accepts."),
    ] = None
    required: Annotated[
        bool | None,
        Field(description="Indicates whether or not this column is required."),
    ] = None
    required_for_non_mac_groupings: Annotated[
        bool | None,
        Field(
            alias="requiredForNonMacGroupings",
            description="Indicates whether or not this column is required when using a non-MAC based account grouping.",
        ),
    ] = None
    allow_blanks: Annotated[
        bool | None,
        Field(
            alias="allowBlanks",
            description="Indicates whether or not this column allows the source column to contain blank values.",
        ),
    ] = None
    alternative_mappings: Annotated[
        list[str] | None,
        Field(
            alias="alternativeMappings",
            description="A list of alternative mappings, identified by their `mindbridgeFieldName`. If all of the alternatives are mapped, then this mapping's `required` constraint is considered satisfied. \n\n**Note**: This column may not be mapped if any alternative is also mapped.",
        ),
    ] = None
    default_value: Annotated[
        str | None,
        Field(
            alias="defaultValue",
            description="A value that is substituted for blank values when `allowBlanks` is false.",
        ),
    ] = None


class ApiAnalysisResultRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="Identifies the associated analysis."),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(alias="analysisTypeId", description="Identifies the type of analysis."),
    ] = None
    interim: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the analysis is using an interim time frame."
        ),
    ] = None
    analysis_periods: Annotated[
        list[ApiAnalysisPeriodRead] | None,
        Field(
            alias="analysisPeriods",
            description="Details about the specific analysis periods under audit.",
        ),
    ] = None
    reporting_period_configuration_id: Annotated[
        str | None,
        Field(
            alias="reportingPeriodConfigurationId",
            description="Identifies the associated reporting period configuration. If null the analysis uses a standard reporting period.",
        ),
    ] = None


class PageablenullRead(BaseItem):
    paged: bool | None = None
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    page_size: Annotated[int | None, Field(alias="pageSize")] = None
    unpaged: bool | None = None
    offset: int | None = None
    sort: SortnullRead | None = None


class ApiAnalysisPeriodCreate(BaseItem):
    start_date: Annotated[
        date | None,
        Field(
            alias="startDate", description="The first day of the period under analysis."
        ),
    ] = None
    interim_as_at_date: Annotated[
        date | None,
        Field(
            alias="interimAsAtDate",
            description="The last day of the interim period under analysis.",
        ),
    ] = None
    end_date: Annotated[
        date | None,
        Field(
            alias="endDate", description="The last day of the period under analysis."
        ),
    ] = None


class ApiAnalysisCreate(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(alias="analysisTypeId", description="Identifies the type of analysis."),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the analysis.", max_length=80, min_length=0),
    ] = None
    interim: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the analysis is using an interim time frame."
        ),
    ] = None
    periodic: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the analysis is using a periodic time frame."
        ),
    ] = None
    analysis_periods: Annotated[
        list[ApiAnalysisPeriodCreate] | None,
        Field(
            alias="analysisPeriods",
            description="Details about the specific analysis periods under audit.",
        ),
    ] = None
    currency_code: Annotated[
        str | None,
        Field(
            alias="currencyCode",
            description="The currency to be displayed across the analysis results.",
        ),
    ] = None
    reference_id: Annotated[
        str | None,
        Field(
            alias="referenceId",
            description="A reference ID to identify the analysis.",
            max_length=256,
            min_length=0,
        ),
    ] = None


class ApiEngagementRollForwardRequest(BaseItem):
    analysis_id: Annotated[
        str | None,
        Field(
            alias="analysisId", description="Identifies the analysis to roll forward."
        ),
    ] = None
    target_engagement_id: Annotated[
        str | None,
        Field(
            alias="targetEngagementId",
            description="Identifies the engagement that the analysis will be rolled forward into.",
        ),
    ] = None
    interim: Annotated[
        bool | None,
        Field(
            description="When `true`, the new analysis period will use an interim time frame."
        ),
    ] = None


class RunAdminReportRequestCreate(BaseItem):
    start: Annotated[
        AwareDatetime | None,
        Field(description="The first date in the reporting timeframe."),
    ] = None
    end: Annotated[
        AwareDatetime | None,
        Field(description="The last date in the reporting timeframe."),
    ] = None


class RunAnalysisOverviewReportRequestCreate(BaseItem):
    include_amount_value: Annotated[
        bool | None,
        Field(
            alias="includeAmountValue",
            description="Indicates whether to include amount value. Defaults to `false` if not specified.",
        ),
    ] = None
    include_entries_percentage_value: Annotated[
        bool | None,
        Field(
            alias="includeEntriesPercentageValue",
            description="Indicates whether to include entries percentage value. Defaults to `false` if not specified.",
        ),
    ] = None
    include_amount_percentage_value: Annotated[
        bool | None,
        Field(
            alias="includeAmountPercentageValue",
            description="Indicates whether to include amount percentage value. Defaults to `false` if not specified.",
        ),
    ] = None
    include_control_point_and_weights: Annotated[
        bool | None,
        Field(
            alias="includeControlPointAndWeights",
            description="Indicates whether to include control point and weights. Defaults to `false` if not specified.",
        ),
    ] = None
    user_time_zone: Annotated[
        str | None,
        Field(
            alias="userTimeZone",
            description="Time zone to use for certain times in the export. Defaults to `UTC` if not specified or if the provided timezone string value is unable to be determined.",
        ),
    ] = None
    csv_export: Annotated[
        bool | None,
        Field(
            alias="csvExport",
            description="Indicates to export as a CSV file format instead of Excel. Defaults to `true` if not specified.",
        ),
    ] = None
    analysis_ids: Annotated[
        list[str] | None,
        Field(
            alias="analysisIds",
            description="The analysis ids to include. If not provided or empty, all will be included.",
        ),
    ] = None
    risk_score_ids: Annotated[
        list[str] | None,
        Field(
            alias="riskScoreIds",
            description="The risk score ids being filtered. If not provided, all will be included.",
        ),
    ] = None


class RunActivityReportRequestCreateCategory(str, Enum):
    ACCOUNT_GROUPING = "ACCOUNT_GROUPING"
    ACCOUNT_MAPPING = "ACCOUNT_MAPPING"
    ADMIN_REPORT = "ADMIN_REPORT"
    ANALYSIS = "ANALYSIS"
    ANALYSIS_SETTINGS = "ANALYSIS_SETTINGS"
    ANALYSIS_TYPE = "ANALYSIS_TYPE"
    API_TOKEN = "API_TOKEN"
    AUDIT_ANNOTATION = "AUDIT_ANNOTATION"
    COLLECTION_ASSIGNMENT = "COLLECTION_ASSIGNMENT"
    CUSTOM_CONTROL_POINT = "CUSTOM_CONTROL_POINT"
    ENGAGEMENT = "ENGAGEMENT"
    ENGAGEMENT_ACCOUNT_GROUP = "ENGAGEMENT_ACCOUNT_GROUP"
    FILE_LOCKER = "FILE_LOCKER"
    FILE_MANAGER = "FILE_MANAGER"
    FILTER = "FILTER"
    GDPDU = "GDPDU"
    INGESTION = "INGESTION"
    INTEGRATIONS = "INTEGRATIONS"
    LIBRARY = "LIBRARY"
    MIGRATION = "MIGRATION"
    ORGANIZATION = "ORGANIZATION"
    POPULATION = "POPULATION"
    QUERY = "QUERY"
    RATIO = "RATIO"
    REPORT_BUILDER = "REPORT_BUILDER"
    REPORT = "REPORT"
    RESULTS_EXPORT = "RESULTS_EXPORT"
    RISK_RANGES = "RISK_RANGES"
    RISK_SEGMENTATION_DASHBOARD = "RISK_SEGMENTATION_DASHBOARD"
    SCIM_API = "SCIM_API"
    SUPPORT_ACCESS = "SUPPORT_ACCESS"
    TASK = "TASK"
    USER = "USER"
    WORKFLOW = "WORKFLOW"
    PAGE_VIEW = "PAGE_VIEW"
    ANALYSIS_SOURCE = "ANALYSIS_SOURCE"
    WEBHOOK = "WEBHOOK"
    PROCEDURE_INSTANCE = "PROCEDURE_INSTANCE"
    CLOUD_ELEMENTS = "CLOUD_ELEMENTS"
    ENGAGEMENT_ACCOUNT_GROUPING_NODE = "ENGAGEMENT_ACCOUNT_GROUPING_NODE"


class RunActivityReportRequestCreate(BaseItem):
    start: Annotated[
        AwareDatetime | None,
        Field(description="The first date in the reporting timeframe."),
    ] = None
    end: Annotated[
        AwareDatetime | None,
        Field(description="The last date in the reporting timeframe."),
    ] = None
    user_ids: Annotated[
        list[str] | None,
        Field(
            alias="userIds",
            description="The users to include in the report. If empty, all users will be included.",
        ),
    ] = None
    categories: Annotated[
        list[RunActivityReportRequestCreateCategory] | None,
        Field(
            description="The categories to include in the report. If empty, all categories will be included."
        ),
    ] = None
    only_completed_analyses: Annotated[
        bool | None,
        Field(
            alias="onlyCompletedAnalyses",
            description="Restrict entries to analysis complete events.",
        ),
    ] = None


class ApiVerifyAccountsRequest(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="The unique identifier of the engagement to verify accounts for.",
        ),
    ] = None


class ApiExportAccountsRequest(BaseItem):
    engagement_id: Annotated[str | None, Field(alias="engagementId")] = None


class ApiDeleteUnusedAccountMappingsRequest(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="The unique identifier of the engagement to delete unused account mappings for.",
        ),
    ] = None


class ApiImportAccountGroupingParamsUpdate(BaseItem):
    chunked_file_id: Annotated[
        str | None,
        Field(
            alias="chunkedFileId",
            description="The unique identifier of the chunked file that contains the account grouping data.",
        ),
    ] = None


class ApiAccountGroupingPublishStatus(str, Enum):
    """The current status of the account grouping."""

    DRAFT = "DRAFT"
    UNPUBLISHED_CHANGES = "UNPUBLISHED_CHANGES"
    PUBLISHED = "PUBLISHED"


class ApiAccountGrouping(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="The data integrity version, to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfo | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfo | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    name: Annotated[
        dict[str, str] | None, Field(description="The name of the account grouping.")
    ] = None
    code_display_name: Annotated[
        dict[str, str] | None,
        Field(
            alias="codeDisplayName",
            description="The name of the account code hierarchy system used within the dataset.",
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The delimiter character used to separate each category level in an account grouping code."
        ),
    ] = None
    mac: Annotated[
        bool | None,
        Field(
            description="When `true`, the account grouping is based on the MAC code system."
        ),
    ] = None
    system: Annotated[
        bool | None,
        Field(
            description="When `true`, the account grouping is a system account grouping and cannot be modified."
        ),
    ] = None
    archived: Annotated[
        bool | None, Field(description="When `true`, the account grouping is archived.")
    ] = None
    published_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="publishedDate",
            description="The date that the account grouping was published.",
        ),
    ] = None
    publish_status: Annotated[
        ApiAccountGroupingPublishStatus | None,
        Field(
            alias="publishStatus",
            description="The current status of the account grouping.",
        ),
    ] = None


class ApiImportAccountGroupingParamsCreateType(str, Enum):
    """The type of account grouping file being imported."""

    MINDBRIDGE_TEMPLATE = "MINDBRIDGE_TEMPLATE"
    CCH_GROUP_TRIAL_BALANCE = "CCH_GROUP_TRIAL_BALANCE"


class ApiImportAccountGroupingParamsCreate(BaseItem):
    name: Annotated[
        str | None, Field(description="The name of the new account grouping.")
    ] = None
    type: Annotated[
        ApiImportAccountGroupingParamsCreateType | None,
        Field(description="The type of account grouping file being imported."),
    ] = None
    chunked_file_id: Annotated[
        str | None,
        Field(
            alias="chunkedFileId",
            description="The unique identifier of the chunked file that contains the account grouping data.",
        ),
    ] = None


class ApiBasicMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiColumnDateTimeFormat(BaseItem):
    selected: Annotated[
        bool | None,
        Field(
            description="If true, this format was selected during column mapping as the correct format for this column."
        ),
    ] = None
    custom_format_pattern: Annotated[
        str | None,
        Field(
            alias="customFormatPattern", description="The pattern of this date format."
        ),
    ] = None
    sample_raw_values: Annotated[
        list[str] | None,
        Field(alias="sampleRawValues", description="A list of values in this column."),
    ] = None
    sample_converted_values: Annotated[
        list[AwareDatetime] | None,
        Field(
            alias="sampleConvertedValues",
            description="A list of date time values derived by parsing the text using this format.",
        ),
    ] = None


class ApiCountMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiCurrencyFormat(BaseItem):
    decimal_character: Annotated[
        str | None,
        Field(
            alias="decimalCharacter",
            description="The character used as a decimal separator.",
        ),
    ] = None
    non_decimal_delimiters: Annotated[
        list[str] | None,
        Field(
            alias="nonDecimalDelimiters",
            description="Non decimal separator special characters, including currency and grouping characters.",
        ),
    ] = None
    ambiguous_delimiters: Annotated[
        list[str] | None,
        Field(
            alias="ambiguousDelimiters",
            description="A list of possible delimiter characters, if multiple possible candidates are available.",
        ),
    ] = None
    example: Annotated[str | None, Field(description="An example value.")] = None


class ApiDataPreview(BaseItem):
    row: Annotated[
        int | None, Field(description="The row number within the table.")
    ] = None
    column: Annotated[
        int | None, Field(description="The column index within the row.")
    ] = None
    data: Annotated[
        str | None, Field(description="The value within the target row.")
    ] = None


class ApiDataTypeMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiDataTypeMetricsDetectedType(str, Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    UNKNOWN = "UNKNOWN"
    FLOAT64 = "FLOAT64"


class ApiDataTypeMetricsDominantType(str, Enum):
    """The type determined to be the most prevalent in this column."""

    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    UNKNOWN = "UNKNOWN"
    FLOAT64 = "FLOAT64"


class ApiDensityMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiDensityMetrics(BaseItem):
    state: Annotated[
        ApiDensityMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )
    density: Annotated[
        float | None,
        Field(
            description="The percentage density of values against blanks, represented as decimal between 1 and 0."
        ),
    ] = None
    blanks: Annotated[int | None, Field(description="The number of blank values.")] = (
        None
    )


class ApiDistinctValueMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiDistinctValueMetrics(BaseItem):
    state: Annotated[
        ApiDistinctValueMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )


class ApiHistogramMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiHistogramMetrics(BaseItem):
    state: Annotated[
        ApiHistogramMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )
    histogram: Annotated[
        dict[str, int] | None,
        Field(
            description="A map of the number of columns to the number of rows with that many columns, in the case of unevenColumnsMetrics."
        ),
    ] = None


class ApiOverallDataTypeMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiOverallDataTypeMetrics(BaseItem):
    state: Annotated[
        ApiOverallDataTypeMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    cell_type_counts: Annotated[
        dict[str, int] | None,
        Field(
            alias="cellTypeCounts",
            description="A map of data types to the number of cells in the table of that data type.",
        ),
    ] = None
    column_type_counts: Annotated[
        dict[str, int] | None,
        Field(
            alias="columnTypeCounts",
            description="A map of data types to the number of columns in the table of that data type.",
        ),
    ] = None
    total_records: Annotated[
        int | None,
        Field(alias="totalRecords", description="The total number of values."),
    ] = None
    blank_records: Annotated[
        int | None,
        Field(alias="blankRecords", description="The number of blank values."),
    ] = None
    column_count: Annotated[
        int | None, Field(alias="columnCount", description="The number of columns.")
    ] = None
    total_rows: Annotated[
        int | None, Field(alias="totalRows", description="The total number of rows.")
    ] = None


class ApiSheetMetricsState(str, Enum):
    """Validation state of the metric within its context."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ApiSheetMetrics(BaseItem):
    state: Annotated[
        ApiSheetMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )
    sheet_names: Annotated[
        list[str] | None,
        Field(
            alias="sheetNames",
            description="A list of sheet names within the underlying Excel file.",
        ),
    ] = None
    valid_sheets: Annotated[
        list[str] | None,
        Field(
            alias="validSheets",
            description="A list of usable sheet names within the underlying Excel file.",
        ),
    ] = None


class RangeBigDecimal(BaseItem):
    min: float | None = None
    max: float | None = None


class RangeInteger(BaseItem):
    min: int | None = None
    max: int | None = None


class RangeZonedDateTime(BaseItem):
    min: AwareDatetime | None = None
    max: AwareDatetime | None = None


class ApiEffectiveDateMetricsReadPeriodType(str, Enum):
    """Indicates the time period by which the histogram has been broken down."""

    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"


class ApiEffectiveDateMetricsRead(BaseItem):
    period_type: Annotated[
        ApiEffectiveDateMetricsReadPeriodType | None,
        Field(
            alias="periodType",
            description="Indicates the time period by which the histogram has been broken down.",
        ),
    ] = None
    entries_in_period: Annotated[
        int | None,
        Field(
            alias="entriesInPeriod",
            description="The number of entries that occurred within the source period's date range.",
        ),
    ] = None
    entries_out_of_period: Annotated[
        int | None,
        Field(
            alias="entriesOutOfPeriod",
            description="The number of entries that occurred outside of the source period's date range.",
        ),
    ] = None
    debits_in_period: Annotated[
        float | None,
        Field(
            alias="debitsInPeriod",
            description="The total debit amount that occurred within the source period's date range.",
        ),
    ] = None
    credits_in_period: Annotated[
        float | None,
        Field(
            alias="creditsInPeriod",
            description="The total credit amount that occurred within the source period's date range.",
        ),
    ] = None
    in_period_count_histogram: Annotated[
        dict[str, int] | None,
        Field(
            alias="inPeriodCountHistogram",
            description="A map showing the total number of entries that occurred within each indicated date period.",
        ),
    ] = None
    out_of_period_count_histogram: Annotated[
        dict[str, int] | None,
        Field(
            alias="outOfPeriodCountHistogram",
            description="A map showing the total number of entries that occurred outside of each indicated date period.",
        ),
    ] = None


class ApiAnalysisSourceStatusReadStatus(str, Enum):
    """The current state of the analysis source."""

    IMPORTING = "IMPORTING"
    UPLOADING = "UPLOADING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ApiAnalysisSourceStatusRead(BaseItem):
    source_id: Annotated[
        str | None,
        Field(alias="sourceId", description="Identifies the analysis source object."),
    ] = None
    analysis_source_type_id: Annotated[
        str | None,
        Field(
            alias="analysisSourceTypeId",
            description="Identifies the analysis source type.",
        ),
    ] = None
    status: Annotated[
        ApiAnalysisSourceStatusReadStatus | None,
        Field(description="The current state of the analysis source."),
    ] = None
    period_id: Annotated[
        str | None,
        Field(
            alias="periodId",
            description="Identifies the analysis period within the analysis.",
        ),
    ] = None


class ApiAnalysisStatusReadPreflightError(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    NOT_READY = "NOT_READY"
    ARCHIVED = "ARCHIVED"
    REQUIRED_FILES_MISSING = "REQUIRED_FILES_MISSING"
    SOURCES_NOT_READY = "SOURCES_NOT_READY"
    SOURCE_ERROR = "SOURCE_ERROR"
    UNVERIFIED_ACCOUNT_MAPPINGS = "UNVERIFIED_ACCOUNT_MAPPINGS"
    ANALYSIS_PERIOD_OVERLAP = "ANALYSIS_PERIOD_OVERLAP"
    SOURCE_WARNINGS_PRESENT = "SOURCE_WARNINGS_PRESENT"


class ApiAnalysisStatusReadStatus(str, Enum):
    """The current state of the analysis."""

    NOT_STARTED = "NOT_STARTED"
    IMPORTING_FILE = "IMPORTING_FILE"
    PREPARING_DATA = "PREPARING_DATA"
    PROCESSING = "PROCESSING"
    CONSOLIDATING_RESULTS = "CONSOLIDATING_RESULTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApiAnalysisStatusRead(BaseItem):
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="Identifies the associated analysis."),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(alias="analysisTypeId", description="Identifies the type of analysis."),
    ] = None
    preflight_errors: Annotated[
        list[ApiAnalysisStatusReadPreflightError] | None,
        Field(
            alias="preflightErrors",
            description="The errors that occurred before the analysis was run.",
        ),
    ] = None
    source_statuses: Annotated[
        list[ApiAnalysisSourceStatusRead] | None,
        Field(
            alias="sourceStatuses",
            description="Details about the state of each analysis source.",
        ),
    ] = None
    available_features: Annotated[
        dict[str, bool] | None,
        Field(
            alias="availableFeatures",
            description="Details about the various analysis capabilities available in MindBridge. [Learn more](https://support.mindbridge.ai/hc/en-us/articles/360056395234)",
        ),
    ] = None
    status: Annotated[
        ApiAnalysisStatusReadStatus | None,
        Field(description="The current state of the analysis."),
    ] = None
    ready: Annotated[
        bool | None,
        Field(description="Indicates whether or not the analysis is ready to be run."),
    ] = None
    mapped_account_mapping_count: Annotated[
        int | None,
        Field(
            alias="mappedAccountMappingCount",
            description="The number of mapped accounts.",
        ),
    ] = None
    unmapped_account_mapping_count: Annotated[
        int | None,
        Field(
            alias="unmappedAccountMappingCount",
            description="The number of unmapped accounts.",
        ),
    ] = None
    inferred_account_mapping_count: Annotated[
        int | None,
        Field(
            alias="inferredAccountMappingCount",
            description="The number of inferred account mapping; this can be considered a warning on partial matches.",
        ),
    ] = None
    re_run_ready: Annotated[
        bool | None,
        Field(
            alias="reRunReady",
            description="Indicates whether or not the analysis is ready to be run again.",
        ),
    ] = None


class MindBridgeQueryTermMindBridgeQueryTerm(BaseItem):
    field_eq: Annotated[int | float | bool | str | None, Field(alias="$eq")] = None


class MindBridgeQueryTermMindBridgeQueryTerm1(BaseItem):
    field_ne: Annotated[int | float | bool | str | None, Field(alias="$ne")] = None


class MindBridgeQueryTermMindBridgeQueryTerm2(BaseItem):
    field_gt: Annotated[int | float | str | None, Field(alias="$gt")] = None


class MindBridgeQueryTermMindBridgeQueryTerm3(BaseItem):
    field_gte: Annotated[int | float | str | None, Field(alias="$gte")] = None


class MindBridgeQueryTermMindBridgeQueryTerm4(BaseItem):
    field_lt: Annotated[int | float | str | None, Field(alias="$lt")] = None


class MindBridgeQueryTermMindBridgeQueryTerm5(BaseItem):
    field_lte: Annotated[int | float | str | None, Field(alias="$lte")] = None


class MindBridgeQueryTermMindBridgeQueryTerm6(BaseItem):
    field_contains: Annotated[list[str] | None, Field(alias="$contains")] = None


class MindBridgeQueryTermMindBridgeQueryTerm8(BaseItem):
    field_in: Annotated[list[int | float | bool | str] | None, Field(alias="$in")] = (
        None
    )


class MindBridgeQueryTermMindBridgeQueryTerm9(BaseItem):
    field_nin: Annotated[list[int | float | bool | str] | None, Field(alias="$nin")] = (
        None
    )


class MindBridgeQueryTermMindBridgeQueryTerm10(BaseItem):
    field_flags: Annotated[dict[str, bool] | None, Field(alias="$flags")] = None


class MindBridgeQueryTermMindBridgeQueryTerm11(BaseItem):
    field_isubstr: Annotated[str | None, Field(alias="$isubstr")] = None


class MindBridgeQueryTermMindBridgeQueryTerm12(BaseItem):
    field_iprefix: Annotated[str | None, Field(alias="$iprefix")] = None


class MindBridgeQueryTermMindBridgeQueryTerm13(BaseItem):
    field_niprefix: Annotated[str | None, Field(alias="$niprefix")] = None


class MindBridgeQueryTermMindBridgeQueryTerm16(BaseItem):
    field_keyword_prefix: Annotated[str | None, Field(alias="$keyword_prefix")] = None


class MindBridgeQueryTermMindBridgeQueryTerm17(BaseItem):
    field_keyword_prefix_not: Annotated[
        str | None, Field(alias="$keyword_prefix_not")
    ] = None


class JsonTableBodyJsonTableBody(BaseItem):
    pass


JsonTableBody = RootModel[
    list[list[int | float | bool | str] | JsonTableBodyJsonTableBody] | None
]


class AnalysisResultWebhookPayload(BaseItem):
    type: Annotated[
        AnalysisResultWebhookPayloadType | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        AnalysisResultWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class AnalysisSourceWebhookPayload(BaseItem):
    type: Annotated[
        AnalysisSourceWebhookPayloadType | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        AnalysisSourceWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class EngagementSubscriptionWebhookPayload(BaseItem):
    type: Annotated[
        Literal["unmapped.accounts"] | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        EngagementSubscriptionWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class EngagementWebhookPayload(BaseItem):
    type: Annotated[
        EngagementWebhookPayloadType | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        EngagementWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class FileManagerWebhookPayload(BaseItem):
    type: Annotated[
        FileManagerWebhookPayloadType | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        FileManagerWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class UserWebhookPayload(BaseItem):
    type: Annotated[
        Literal["user.deleted"] | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        UserWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class UserRoleWebhookPayload(BaseItem):
    type: Annotated[
        UserRoleWebhookPayloadType | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        UserRoleWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class UserLoginWebhookPayload(BaseItem):
    type: Annotated[
        Literal["user.login"] | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        UserLoginWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class UserStatusWebhookPayload(BaseItem):
    type: Annotated[
        Literal["user.status"] | None,
        Field(description="The event type that triggered the webhook."),
    ] = None
    event_id: Annotated[
        ObjectId | None,
        Field(
            alias="eventId",
            description="The ID of the event that triggered the outbound request.",
        ),
    ] = None
    timestamp: Annotated[
        AwareDatetime | None,
        Field(description="The time that the webhook was triggered."),
    ] = None
    sender_id: Annotated[
        ObjectId | None,
        Field(
            alias="senderId",
            description="The ID of the registered webhook configuration that initiated the outbound request.",
        ),
    ] = None
    tenant_id: Annotated[
        str | None,
        Field(
            alias="tenantId",
            description="The name of the tenant that triggered the webhook.",
        ),
    ] = None
    user_id: Annotated[
        ObjectId | None,
        Field(
            alias="userId",
            description="The ID of the user that initiated the event that triggered the webhook.",
        ),
    ] = None
    data: Annotated[
        UserStatusWebhookData | None,
        Field(description="The data associated with the webhook event."),
    ] = None


class ApiTaskRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_result_id: Annotated[str | None, Field(alias="analysisResultId")] = None
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="Identifies the associated analysis."),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(
            alias="analysisTypeId",
            description="Identifies the associated analysis type.",
        ),
    ] = None
    transaction: Annotated[
        str | None, Field(description="The name of the associated transaction.")
    ] = None
    name: Annotated[
        str | None,
        Field(
            description="The task's name. Generated based on on the related entry or transaction."
        ),
    ] = None
    row_id: Annotated[
        int | None, Field(alias="rowId", description="Identifies the associated entry.")
    ] = None
    transaction_id: Annotated[
        int | None,
        Field(
            alias="transactionId", description="Identifies the associated transaction."
        ),
    ] = None
    status: Annotated[
        ApiTaskReadStatus | None,
        Field(description="The current state of the task.", title="Task Status"),
    ] = None
    assigned_id: Annotated[
        str | None,
        Field(
            alias="assignedId", description="Identifies the user assigned to this task."
        ),
    ] = None
    description: Annotated[
        str | None, Field(description="A description of the task.")
    ] = None
    comments: Annotated[
        list[ApiTaskCommentRead] | None,
        Field(
            description="A list of all the comments that have been made on this task."
        ),
    ] = None
    sample: Annotated[
        str | None, Field(description="Which sample this task is a part of.")
    ] = None
    audit_areas: Annotated[
        list[str] | None,
        Field(
            alias="auditAreas",
            description="Which audit areas this task is associated with.",
        ),
    ] = None
    assertions: Annotated[
        list[str] | None,
        Field(description="Which assertions this task is associated with."),
    ] = None
    type: Annotated[
        ApiTaskReadType | None,
        Field(
            description="The type of entry this task is associated with.",
            title="Task Type",
        ),
    ] = None
    sample_type: Annotated[
        ApiTaskReadSampleType | None,
        Field(
            alias="sampleType",
            description="The sampling method used to create this task.",
            title="Sample Type",
        ),
    ] = None
    entry_type: Annotated[
        str | None,
        Field(
            alias="entryType",
            description="For AP and AR analyses this is the entry type for the associated entry.",
        ),
    ] = None
    vendor_name: Annotated[
        str | None,
        Field(
            alias="vendorName",
            description="For AP analyses this is the vendor name for the associated entry.",
        ),
    ] = None
    customer_name: Annotated[
        str | None,
        Field(
            alias="customerName",
            description="For AR analyses this is the customer name for the associated entry.",
        ),
    ] = None
    invoice_ref: Annotated[
        str | None,
        Field(
            alias="invoiceRef",
            description="For AP and AR analyses this is the Invoice ref value for the associated entry.",
        ),
    ] = None
    credit_value: Annotated[
        int | None,
        Field(
            alias="creditValue",
            deprecated=True,
            description="The credit value of the associated transaction or entry, formatted as MONEY_100.",
        ),
    ] = None
    debit_value: Annotated[
        int | None,
        Field(
            alias="debitValue",
            deprecated=True,
            description="The debit value of the associated transaction or entry, formatted as MONEY_100.",
        ),
    ] = None
    risk_scores: Annotated[
        dict[str, int] | None,
        Field(
            alias="riskScores",
            description="A map of ensemble names or IDs mapped to their risk score value. The value is a PERCENTAGE_FIXED_POINT type.",
        ),
    ] = None
    filter_statement: Annotated[
        str | None,
        Field(
            alias="filterStatement",
            description="The filter statement that was applied when creating this task via a bulk task creation.",
        ),
    ] = None
    task_approval_status: Annotated[
        ApiTaskReadTaskApprovalStatus | None,
        Field(alias="taskApprovalStatus", title="Task Approval Status"),
    ] = None
    due_date: Annotated[date | None, Field(alias="dueDate")] = None
    approver_id: Annotated[str | None, Field(alias="approverId")] = None
    tags: list[str] | None = None
    amounts: dict[str, MoneyRead] | None = None


class ApiFilterAccountConditionApiFilterAccountCondition13(BaseItem):
    type: Annotated[
        Literal["ACCOUNT_NODE_ARRAY"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "ACCOUNT_NODE_ARRAY"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    account_selections: Annotated[
        list[ApiFilterAccountSelection] | None, Field(alias="accountSelections")
    ] = None


class ApiFilterControlPointConditionApiFilterControlPointCondition13(BaseItem):
    type: Annotated[
        Literal["CONTROL_POINT"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "CONTROL_POINT"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel | None,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ] = None
    control_points: Annotated[
        list[ApiFilterControlPointSelection] | None,
        Field(alias="controlPoints", description="A list of control point selections."),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13(BaseItem):
    type: Annotated[
        Literal["TYPEAHEAD_ENTRY"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "TYPEAHEAD_ENTRY"
    field: str | None = None
    field_label: Annotated[str | None, Field(alias="fieldLabel")] = None
    negated: bool | None = None
    full_condition_description: Annotated[
        str | None, Field(alias="fullConditionDescription")
    ] = None
    values: Annotated[
        list[ApiTypeaheadEntry] | None,
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ] = None


class ApiLibraryRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(
            description="The current name of the library.", max_length=80, min_length=0
        ),
    ] = None
    based_on_library_id: Annotated[
        str | None,
        Field(
            alias="basedOnLibraryId",
            description="Identifies the library that the new library is based on. This may be a user-created library or a MindBridge system library.",
        ),
    ] = None
    original_system_library_id: Annotated[
        str | None,
        Field(
            alias="originalSystemLibraryId",
            description="Identifies the original MindBridge-supplied library.",
        ),
    ] = None
    warnings_dismissed: Annotated[
        bool | None,
        Field(
            alias="warningsDismissed",
            description="When set to `true`, any conversion warnings for this library will not be displayed in the **Libraries** tab in the UI.",
        ),
    ] = None
    conversion_warnings: Annotated[
        list[ProblemRead] | None,
        Field(
            alias="conversionWarnings",
            description="A list of accounts that failed to convert the selected base library's setting to the selected account grouping.",
        ),
    ] = None
    account_grouping_id: Annotated[
        str | None,
        Field(
            alias="accountGroupingId",
            description="Identifies the account grouping used.",
        ),
    ] = None
    analysis_type_ids: Annotated[
        list[str] | None,
        Field(
            alias="analysisTypeIds",
            description="Identifies the analysis types used in the library.",
        ),
    ] = None
    default_delimiter: Annotated[
        str | None,
        Field(
            alias="defaultDelimiter",
            description="Identifies the default delimiter used in imported CSV files.",
        ),
    ] = None
    control_point_selection_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointSelectionPermission",
            description="When set to `true`, control points can be added or removed within each risk score.",
        ),
    ] = None
    control_point_weight_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointWeightPermission",
            description="When set to `true`, the weight of each control point can be adjusted within each risk score.",
        ),
    ] = None
    control_point_settings_permission: Annotated[
        bool | None,
        Field(
            alias="controlPointSettingsPermission",
            description="When set to `true`, individual control point settings can be adjusted within each risk score.",
        ),
    ] = None
    risk_score_and_groups_selection_permission: Annotated[
        bool | None,
        Field(
            alias="riskScoreAndGroupsSelectionPermission",
            description="When set to `true`, risk scores and groups can be disabled, and accounts associated with risk scores can be edited.",
        ),
    ] = None
    risk_range_edit_permission: Annotated[
        bool | None, Field(alias="riskRangeEditPermission")
    ] = None
    risk_score_display: Annotated[
        ApiLibraryReadRiskScoreDisplay | None,
        Field(
            alias="riskScoreDisplay",
            description="Determines whether risk scores will be presented as percentages (%), or using High, Medium, and Low label indicators.",
        ),
    ] = None
    system: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the library is a MindBridge system library."
        ),
    ] = None
    archived: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the library is archived. Archived libraries cannot be selected when creating an engagement."
        ),
    ] = None


class ApiFileManagerDirectoryUpdate(ApiFileManagerEntityUpdate):
    name: Annotated[str | None, Field(description="The name of the directory.")] = None
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiFileManagerDirectoryRead(ApiFileManagerEntityRead):
    name: Annotated[str | None, Field(description="The name of the directory.")] = None
    engagement_id: Annotated[
        str,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiAnalysisConfigUpdate(BaseItem):
    risk_groups: Annotated[
        list[ApiRiskGroupUpdate] | None,
        Field(
            alias="riskGroups",
            description="The list of risk groups associated with this analysis config.",
        ),
    ] = None


class ApiAnalysisTypeConfigurationUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    system: bool | None = None
    configuration: Annotated[
        ApiAnalysisConfigUpdate | None,
        Field(description="The configuration details for this analysis type."),
    ] = None


class ApiAnalysisConfigRead(BaseItem):
    risk_groups: Annotated[
        list[ApiRiskGroupRead] | None,
        Field(
            alias="riskGroups",
            description="The list of risk groups associated with this analysis config.",
        ),
    ] = None


class ApiAnalysisTypeConfigurationRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    system: bool | None = None
    library_id: Annotated[
        str | None,
        Field(
            alias="libraryId",
            description="Identifies the library associated with this configuration.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_id: Annotated[
        str | None,
        Field(
            alias="analysisId",
            description="Identifies the analysis associated with this configuration.",
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(alias="analysisTypeId", description="Identifies the type of analysis."),
    ] = None
    configuration: Annotated[
        ApiAnalysisConfigRead | None,
        Field(description="The configuration details for this analysis type."),
    ] = None
    control_point_bundle_version: Annotated[
        str | None,
        Field(
            alias="controlPointBundleVersion",
            description="The version of the control point bundle used in this configuration.",
        ),
    ] = None
    template: Annotated[
        bool | None,
        Field(description="Indicates whether this configuration is a template."),
    ] = None


class ApiDuplicateVirtualColumnUpdate(ApiVirtualColumnUpdate):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the duplicated column."
        ),
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnUpdateType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiJoinVirtualColumnUpdate(ApiVirtualColumnUpdate):
    column_indices: Annotated[
        list[int] | None,
        Field(alias="columnIndices", description="The position of the joined column."),
    ] = None
    delimiter: Annotated[
        str | None, Field(description="The character(s) used to separate values.")
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnUpdateType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiProposedDuplicateVirtualColumnUpdate(ApiProposedVirtualColumnUpdate):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex",
            description="The position of the column to be duplicated.",
        ),
    ] = None


class ApiProposedJoinVirtualColumnUpdate(ApiProposedVirtualColumnUpdate):
    column_indices: Annotated[
        list[int] | None,
        Field(
            alias="columnIndices",
            description="The positions of the columns to be joined.",
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The character(s) that should be inserted to separate values."
        ),
    ] = None


class ApiProposedSplitByDelimiterVirtualColumnUpdate(ApiProposedVirtualColumnUpdate):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the column to be split."
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The character(s) that should be used to separate the string into parts."
        ),
    ] = None
    split_index: Annotated[
        int | None,
        Field(
            alias="splitIndex",
            description="The position of the part to be used as a virtual column.",
        ),
    ] = None


class ApiProposedSplitByPositionVirtualColumnUpdate(ApiProposedVirtualColumnUpdate):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the column to be split."
        ),
    ] = None
    start_position: Annotated[
        int | None,
        Field(
            alias="startPosition",
            description="The starting position of the substring to be used as the new column. **Inclusive**.",
        ),
    ] = None
    end_position: Annotated[
        int | None,
        Field(
            alias="endPosition",
            description="The ending position of the substring to be used as the new column. **Exclusive**.",
        ),
    ] = None


class ApiSplitByDelimiterVirtualColumnUpdate(ApiVirtualColumnUpdate):
    column_index: Annotated[
        int | None,
        Field(alias="columnIndex", description="The position of the split column."),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(description="The character(s) used to separate the string into parts."),
    ] = None
    split_index: Annotated[
        int | None,
        Field(
            alias="splitIndex",
            description="The position of the part used as a virtual column.",
        ),
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnUpdateType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiSplitByPositionVirtualColumnUpdate(ApiVirtualColumnUpdate):
    column_index: Annotated[
        int | None,
        Field(alias="columnIndex", description="The position of the split column."),
    ] = None
    start_position: Annotated[
        int | None,
        Field(
            alias="startPosition",
            description="The starting position of the substring in the new column. **Inclusive**.",
        ),
    ] = None
    end_position: Annotated[
        int | None,
        Field(
            alias="endPosition",
            description="The ending position of the substring in the new column. **Exclusive**.",
        ),
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnUpdateType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiPageableRead(BaseItem):
    page_number: Annotated[
        int | None,
        Field(
            alias="pageNumber", deprecated=True, description="The current page number."
        ),
    ] = None
    page_size: Annotated[
        int | None,
        Field(
            alias="pageSize",
            deprecated=True,
            description="The number of requested elements on a page.",
        ),
    ] = None
    offset: Annotated[
        int | None,
        Field(
            deprecated=True,
            description="Indicates by how many pages the first page is offset.",
        ),
    ] = None
    sort: Annotated[
        SortnullRead | None,
        Field(deprecated=True, description="Indicates how the data will be sorted."),
    ] = None


class ApiPageApiWebhookEventLogRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiWebhookEventLogRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiUserRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiUserRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiTransactionIdPreviewIndicatorRead(BaseItem):
    rating: Annotated[
        ApiTransactionIdPreviewIndicatorReadRating | None,
        Field(description="The quality of the indicator as rated by MindBridge."),
    ] = None
    value: Annotated[
        Any | None, Field(description="A value for this specific indicator.")
    ] = None
    data: Annotated[
        list[ApiTransactionIdPreviewRowRead] | None,
        Field(description="The set of transactions related to a specific indicator."),
    ] = None


class ApiTransactionIdPreviewRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None, Field(alias="engagementId", deprecated=True)
    ] = None
    analysis_id: Annotated[str | None, Field(alias="analysisId", deprecated=True)] = (
        None
    )
    analysis_source_id: Annotated[
        str | None,
        Field(
            alias="analysisSourceId",
            description="The unique identifier of the associated analysis source.",
        ),
    ] = None
    column_selection: Annotated[
        list[int] | None,
        Field(
            alias="columnSelection",
            description="The list of columns used to generate the transaction ID.",
        ),
    ] = None
    type: Annotated[
        ApiTransactionIdPreviewReadType | None,
        Field(description="The type used when selecting a transaction ID."),
    ] = None
    smart_splitter: Annotated[
        bool | None,
        Field(
            alias="smartSplitter",
            description="Indicates whether or not the Smart Splitter was run when selecting a transaction ID.",
        ),
    ] = None
    overall_rating: Annotated[
        ApiTransactionIdPreviewReadOverallRating | None,
        Field(
            alias="overallRating",
            description="The quality of the transaction ID as rated by MindBridge.",
        ),
    ] = None
    indicators: Annotated[
        dict[str, ApiTransactionIdPreviewIndicatorRead] | None,
        Field(
            description="The data integrity checks used when selecting a transaction ID."
        ),
    ] = None
    entry_previews: Annotated[
        list[ApiTransactionIdPreviewRowRead] | None,
        Field(
            alias="entryPreviews",
            description="Details about the transactions generated by this transaction ID selection.",
        ),
    ] = None


class ApiPageApiTaskRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiTaskRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiTaskHistoryRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiTaskHistoryRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiRiskRangesRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiRiskRangesRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiReportingPeriodConfigurationRequestCreate(BaseItem):
    monthly_reporting_periods: Annotated[
        list[ApiMonthlyReportingPeriodCreate] | None,
        Field(alias="monthlyReportingPeriods"),
    ] = None
    weekly_reporting_periods: Annotated[
        list[ApiWeeklyReportingPeriodCreate] | None,
        Field(alias="weeklyReportingPeriods"),
    ] = None


class ApiReportingPeriodConfigurationRead(BaseItem):
    id: str | None = None
    version: int | None = None
    creation_date: Annotated[AwareDatetime | None, Field(alias="creationDate")] = None
    last_modified_date: Annotated[
        AwareDatetime | None, Field(alias="lastModifiedDate")
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None, Field(alias="createdUserInfo")
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None, Field(alias="lastModifiedUserInfo")
    ] = None
    monthly_reporting_periods: Annotated[
        list[ApiMonthlyReportingPeriodRead] | None,
        Field(
            alias="monthlyReportingPeriods",
            description="List of monthly reporting periods.",
        ),
    ] = None
    weekly_reporting_periods: Annotated[
        list[ApiWeeklyReportingPeriodRead] | None,
        Field(
            alias="weeklyReportingPeriods",
            description="List of weekly reporting periods.",
        ),
    ] = None
    status: ApiReportingPeriodConfigurationReadStatus | None = None


class ApiPageApiReportingPeriodConfigurationRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiReportingPeriodConfigurationRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiOrganizationRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiOrganizationRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiLibraryRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiLibraryRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiFileExportRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiFileExportRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiFileMergeRequestCreate(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    parent_file_manager_entity_id: Annotated[
        str | None,
        Field(
            alias="parentFileManagerEntityId",
            description="Identifies the parent directory. If NULL, the directory is positioned at the root level.",
        ),
    ] = None
    output_file_name: Annotated[
        str | None,
        Field(
            alias="outputFileName",
            description="The name of the file being generated in the requested merge operation.",
        ),
    ] = None
    file_column_mappings: Annotated[
        dict[str, list[int]] | None,
        Field(
            alias="fileColumnMappings",
            deprecated=True,
            description="**Deprecated: use mappings instead.** Reference to the files and the columns to include in the merge operation.",
        ),
    ] = None
    mappings: Annotated[
        list[FileMergeMappingCreate] | None,
        Field(
            description="Ordered list of file/column selections to merge (each entry has fileManagerFileId and its column indexes)."
        ),
    ] = None


class ApiPageApiFileManagerEntityRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiFileManagerDirectoryRead | ApiFileManagerFileRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiBasicMetricsRead(BaseItem):
    state: Annotated[
        ApiBasicMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None


class ApiCountMetricsRead(BaseItem):
    state: Annotated[
        ApiCountMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )


class ApiDateTypeDetailsRead(BaseItem):
    range: Annotated[
        RangeZonedDateTimeRead | None,
        Field(
            description="A pair of values representing the earliest and latest values within this column."
        ),
    ] = None
    ambiguous_date_time_formats: Annotated[
        list[ApiColumnDateTimeFormatRead] | None,
        Field(
            alias="ambiguousDateTimeFormats",
            description="A list of possible date time formats, if multiple possible candidates are available.",
        ),
    ] = None
    unambiguous_date_time_formats: Annotated[
        list[ApiColumnDateTimeFormatRead] | None,
        Field(
            alias="unambiguousDateTimeFormats",
            description="A list of possible date time formats, if multiple possible candidates are available.",
        ),
    ] = None


class ApiNumericTypeDetailsRead(BaseItem):
    range: Annotated[
        RangeBigDecimalRead | None,
        Field(
            description="A pair of values representing the min and max values within this column."
        ),
    ] = None
    currency_format: Annotated[
        ApiCurrencyFormatRead | None,
        Field(
            alias="currencyFormat",
            description="Metadata on the detected number format of this column.",
        ),
    ] = None
    example_pair_from_currency_formatter: Annotated[
        list[str] | None,
        Field(
            alias="examplePairFromCurrencyFormatter",
            description="A pair of values as examples in the event that two or more unambiguous number formats are detected in the same column.",
        ),
    ] = None
    sum: Annotated[
        float | None,
        Field(
            description="The sum of all values in this column, up to a maximum of 10e<sup>50</sup>. Values smaller than 10e<sup>-50</sup> will be rounded up."
        ),
    ] = None
    capped_sum: Annotated[
        bool | None,
        Field(
            alias="cappedSum",
            description="If `true` then the sum is larger than 10e<sup>50</sup>.",
        ),
    ] = None
    capped_max: Annotated[
        bool | None,
        Field(
            alias="cappedMax",
            description="If `true` then at least one individual value is larger than 10e<sup>50</sup>.",
        ),
    ] = None


class ApiTableMetadataRead(BaseItem):
    cell_length_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="cellLengthMetrics",
            description="Metrics regarding cells that are larger than 2000 characters in the table.",
        ),
    ] = None
    density_metrics: Annotated[
        ApiDensityMetricsRead | None,
        Field(
            alias="densityMetrics", description="Metrics regarding whole table density."
        ),
    ] = None
    inconsistent_date_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="inconsistentDateMetrics",
            description="Metrics regarding inconsistent date formats within columns for the entire table.",
        ),
    ] = None
    null_value_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="nullValueMetrics",
            description="Metrics regarding “null” values across the entire table.",
        ),
    ] = None
    numeric_column_metrics: Annotated[
        ApiBasicMetricsRead | None,
        Field(
            alias="numericColumnMetrics",
            description="Metrics regarding numeric columns within the table.",
        ),
    ] = None
    overall_data_type_metrics: Annotated[
        ApiOverallDataTypeMetricsRead | None,
        Field(
            alias="overallDataTypeMetrics",
            description="Metrics regarding detected data types across the entire table.",
        ),
    ] = None
    scientific_notation_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="scientificNotationMetrics",
            description="Metrics regarding scientific notation across the entire table.",
        ),
    ] = None
    sheet_metrics: Annotated[
        ApiSheetMetricsRead | None,
        Field(
            alias="sheetMetrics",
            description="Metrics regarding excel sheets within the underlying excel file.",
        ),
    ] = None
    special_character_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="specialCharacterMetrics",
            description="Metrics regarding special characters across the entire table.",
        ),
    ] = None
    uneven_columns_metrics: Annotated[
        ApiHistogramMetricsRead | None,
        Field(
            alias="unevenColumnsMetrics",
            description="Metrics regarding column length by row.",
        ),
    ] = None


class ApiTextTypeDetailsRead(BaseItem):
    range: Annotated[
        RangeIntegerRead | None,
        Field(
            description="A pair of values representing the min and max length of text values within this column."
        ),
    ] = None


class ApiPageApiEngagementRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiEngagementRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiEngagementAccountGroupRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiEngagementAccountGroupRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiAsyncResult(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfo | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfo | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    type: Annotated[
        ApiAsyncResultType | None,
        Field(description="Indicates the type of job being run."),
    ] = None
    status: Annotated[
        ApiAsyncResultStatus | None,
        Field(description="Indicates the current state of the job."),
    ] = None
    entity_id: Annotated[
        str | None,
        Field(alias="entityId", description="Identifies the entity used in the job."),
    ] = None
    entity_type: Annotated[
        ApiAsyncResultEntityType | None,
        Field(
            alias="entityType",
            description="Identifies the entity type used in the job.",
        ),
    ] = None
    error: Annotated[
        str | None, Field(description="The reason why the async job failed.")
    ] = None
    error_message: Annotated[str | None, Field(alias="errorMessage")] = None


class ApiPageApiEngagementAccountGroupingRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiEngagementAccountGroupingRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiDatabricksAuthorizationRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiDatabricksAuthorizationRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ActionableErrorResponse(BaseItem):
    type: Annotated[
        str | None,
        Field(
            description="Indicates the type of error that occurred. Type values are formatted as URLs."
        ),
    ] = None
    title: Annotated[str | None, Field(description="A description of the error.")] = (
        None
    )
    problems: Annotated[
        list[Problem] | None, Field(description="The reason(s) why the error occurred.")
    ] = None
    instance: Annotated[
        str | None, Field(description="A unique identifier for this request.")
    ] = None
    status: Annotated[
        int | None,
        Field(description="The HTTP status code determined by the error type."),
    ] = None
    origin: Annotated[
        str | None,
        Field(description="The endpoint where this request originated from."),
    ] = None
    problem_count: Annotated[
        int | None,
        Field(alias="problemCount", description="The total number of problems."),
    ] = None
    entity_type: Annotated[
        str | None,
        Field(
            alias="entityType", description="The type of entity impacted by the error."
        ),
    ] = None
    entity_id: Annotated[
        str | None,
        Field(
            alias="entityId", description="Identifies the entity impacted by the error."
        ),
    ] = None


class ApiPageApiDataTableRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiDataTableRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiConnectionDataRequestCreate(BaseItem):
    table_id: Annotated[
        str | None,
        Field(
            alias="tableId",
            description="The identifier of the table to retrieve data from.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="Identifies the engagement that the resulting Data Table will be associated with.",
        ),
    ] = None
    tabular_schema_hint: Annotated[
        ApiTabularSchemaCreate | None,
        Field(
            alias="tabularSchemaHint",
            description="Optional schema hint describing expected column types.",
        ),
    ] = None
    filter: Annotated[
        ShieldQueryTermCreate | None,
        Field(description="Optional filter to apply to the data retrieval."),
    ] = None
    limit: Annotated[
        int | None, Field(description="Maximum number of rows to return.")
    ] = None
    offset: Annotated[
        int | None,
        Field(description="Number of rows to skip before returning results."),
    ] = None


class ApiPageApiConnectionRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiConnectionRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiConnectionTestResultRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiConnectionTestResultRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiConnectionTableRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    tables_result_id: Annotated[
        str | None,
        Field(
            alias="tablesResultId",
            description="The ID of the Connection Tables Result that discovered this table.",
        ),
    ] = None
    connection_id: Annotated[
        str | None,
        Field(
            alias="connectionId",
            description="The ID of the Connection this table belongs to.",
        ),
    ] = None
    table_id: Annotated[
        str | None,
        Field(
            alias="tableId",
            description="The identifier of the table within the external data source.",
        ),
    ] = None
    name: Annotated[str | None, Field(description="The display name of the table.")] = (
        None
    )
    schema_: Annotated[
        ApiTabularSchemaRead | None,
        Field(
            alias="schema",
            description="The schema describing the columns of the table.",
        ),
    ] = None


class ApiPageApiConnectionTableRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiConnectionTableRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiConnectionTablesResultRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiConnectionTablesResultRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiConnectionDataSourceRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiConnectionDataSourceRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiChunkedFileRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiChunkedFileRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiAsyncResultRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAsyncResultRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiApiTokenRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiApiTokenRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiAnalysisTypeRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    name: Annotated[str | None, Field(description="The name of the analysis type.")] = (
        None
    )
    interim_name: Annotated[
        str | None,
        Field(
            alias="interimName",
            description="The name of the analysis type when the analysis uses an interim time frame.",
        ),
    ] = None
    description: Annotated[
        str | None, Field(description="The description of the analysis type.")
    ] = None
    account_mapping_required: Annotated[
        bool | None,
        Field(
            alias="accountMappingRequired",
            description="Indicates whether or not account mapping must be performed.",
        ),
    ] = None
    fund_supported: Annotated[
        bool | None,
        Field(
            alias="fundSupported",
            description="Indicates whether or not the analysis supports restricted and unrestricted funds.",
        ),
    ] = None
    interim_supported: Annotated[
        bool | None,
        Field(
            alias="interimSupported",
            description="Indicates whether or not the analysis supports the interim time frame.",
        ),
    ] = None
    periodic_supported: Annotated[
        bool | None,
        Field(
            alias="periodicSupported",
            description="Indicates whether or not the analysis supports the periodic time frame.",
        ),
    ] = None
    archived: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the analysis type has been archived."
        ),
    ] = None
    max_period: Annotated[
        int | None,
        Field(
            alias="maxPeriod",
            description="A configuration value for the max analysis period.",
        ),
    ] = None
    source_configurations: Annotated[
        list[ApiSourceConfigurationRead] | None,
        Field(
            alias="sourceConfigurations",
            description="A list of analysis source configurations that can be imported into the analysis, as determined by the analysis type.",
        ),
    ] = None


class ApiPageApiAnalysisTypeRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAnalysisTypeRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiAnalysisTypeConfigurationRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAnalysisTypeConfigurationRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiProposedDuplicateVirtualColumnCreate(ApiProposedVirtualColumnCreate):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex",
            description="The position of the column to be duplicated.",
        ),
    ] = None


class ApiProposedJoinVirtualColumnCreate(ApiProposedVirtualColumnCreate):
    column_indices: Annotated[
        list[int] | None,
        Field(
            alias="columnIndices",
            description="The positions of the columns to be joined.",
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The character(s) that should be inserted to separate values."
        ),
    ] = None


class ApiProposedSplitByDelimiterVirtualColumnCreate(ApiProposedVirtualColumnCreate):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the column to be split."
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The character(s) that should be used to separate the string into parts."
        ),
    ] = None
    split_index: Annotated[
        int | None,
        Field(
            alias="splitIndex",
            description="The position of the part to be used as a virtual column.",
        ),
    ] = None


class ApiProposedSplitByPositionVirtualColumnCreate(ApiProposedVirtualColumnCreate):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the column to be split."
        ),
    ] = None
    start_position: Annotated[
        int | None,
        Field(
            alias="startPosition",
            description="The starting position of the substring to be used as the new column. **Inclusive**.",
        ),
    ] = None
    end_position: Annotated[
        int | None,
        Field(
            alias="endPosition",
            description="The ending position of the substring to be used as the new column. **Exclusive**.",
        ),
    ] = None


class ApiDuplicateVirtualColumnRead(ApiVirtualColumnRead):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the duplicated column."
        ),
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnReadType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiJoinVirtualColumnRead(ApiVirtualColumnRead):
    column_indices: Annotated[
        list[int] | None,
        Field(alias="columnIndices", description="The position of the joined column."),
    ] = None
    delimiter: Annotated[
        str | None, Field(description="The character(s) used to separate values.")
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnReadType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiProposedDuplicateVirtualColumnRead(ApiProposedVirtualColumnRead):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex",
            description="The position of the column to be duplicated.",
        ),
    ] = None


class ApiProposedJoinVirtualColumnRead(ApiProposedVirtualColumnRead):
    column_indices: Annotated[
        list[int] | None,
        Field(
            alias="columnIndices",
            description="The positions of the columns to be joined.",
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The character(s) that should be inserted to separate values."
        ),
    ] = None


class ApiProposedSplitByDelimiterVirtualColumnRead(ApiProposedVirtualColumnRead):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the column to be split."
        ),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The character(s) that should be used to separate the string into parts."
        ),
    ] = None
    split_index: Annotated[
        int | None,
        Field(
            alias="splitIndex",
            description="The position of the part to be used as a virtual column.",
        ),
    ] = None


class ApiProposedSplitByPositionVirtualColumnRead(ApiProposedVirtualColumnRead):
    column_index: Annotated[
        int | None,
        Field(
            alias="columnIndex", description="The position of the column to be split."
        ),
    ] = None
    start_position: Annotated[
        int | None,
        Field(
            alias="startPosition",
            description="The starting position of the substring to be used as the new column. **Inclusive**.",
        ),
    ] = None
    end_position: Annotated[
        int | None,
        Field(
            alias="endPosition",
            description="The ending position of the substring to be used as the new column. **Exclusive**.",
        ),
    ] = None


class ApiSplitByDelimiterVirtualColumnRead(ApiVirtualColumnRead):
    column_index: Annotated[
        int | None,
        Field(alias="columnIndex", description="The position of the split column."),
    ] = None
    delimiter: Annotated[
        str | None,
        Field(description="The character(s) used to separate the string into parts."),
    ] = None
    split_index: Annotated[
        int | None,
        Field(
            alias="splitIndex",
            description="The position of the part used as a virtual column.",
        ),
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnReadType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiSplitByPositionVirtualColumnRead(ApiVirtualColumnRead):
    column_index: Annotated[
        int | None,
        Field(alias="columnIndex", description="The position of the split column."),
    ] = None
    start_position: Annotated[
        int | None,
        Field(
            alias="startPosition",
            description="The starting position of the substring in the new column. **Inclusive**.",
        ),
    ] = None
    end_position: Annotated[
        int | None,
        Field(
            alias="endPosition",
            description="The ending position of the substring in the new column. **Exclusive**.",
        ),
    ] = None
    name: Annotated[str, Field(description="The name of the virtual column.")]
    type: Annotated[
        ApiVirtualColumnReadType, Field(description="The type of virtual column.")
    ]
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiAnalysisSourceTypeRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    name: Annotated[
        str | None, Field(description="The name of the analysis source type.")
    ] = None
    interim_name: Annotated[
        str | None,
        Field(
            alias="interimName",
            description="The name of the analysis source type when the analysis uses an interim time frame.",
        ),
    ] = None
    archived: Annotated[
        bool | None,
        Field(
            description="Indicates whether or not the analysis source type is archived."
        ),
    ] = None
    features: Annotated[
        list[ApiAnalysisSourceTypeReadFeature] | None,
        Field(
            description="A list of the features used when importing data for this analysis source type."
        ),
    ] = None
    column_definitions: Annotated[
        list[ApiColumnDefinitionRead] | None,
        Field(
            alias="columnDefinitions",
            description="A list of MindBridge column definitions that this analysis source type supports.",
        ),
    ] = None


class ApiPageApiAnalysisSourceTypeRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAnalysisSourceTypeRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class PageApiAnalysisResultRead(BaseItem):
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    pageable: PageablenullRead | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    first: bool | None = None
    last: bool | None = None
    size: int | None = None
    content: list[ApiAnalysisResultRead] | None = None
    number: int | None = None
    sort: SortnullRead | None = None
    empty: bool | None = None


class ApiPageApiAnalysisRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAnalysisRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiAccountMappingRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAccountMappingRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiAccountGroupRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAccountGroupRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiAccountGroupingRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAccountGroupingRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiBasicMetrics(BaseItem):
    state: Annotated[
        ApiBasicMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None


class ApiCountMetrics(BaseItem):
    state: Annotated[
        ApiCountMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    count: Annotated[int | None, Field(description="The amount of a given metric.")] = (
        None
    )


class ApiDateTypeDetails(BaseItem):
    range: Annotated[
        RangeZonedDateTime | None,
        Field(
            description="A pair of values representing the earliest and latest values within this column."
        ),
    ] = None
    ambiguous_date_time_formats: Annotated[
        list[ApiColumnDateTimeFormat] | None,
        Field(
            alias="ambiguousDateTimeFormats",
            description="A list of possible date time formats, if multiple possible candidates are available.",
        ),
    ] = None
    unambiguous_date_time_formats: Annotated[
        list[ApiColumnDateTimeFormat] | None,
        Field(
            alias="unambiguousDateTimeFormats",
            description="A list of possible date time formats, if multiple possible candidates are available.",
        ),
    ] = None


class ApiNumericTypeDetails(BaseItem):
    range: Annotated[
        RangeBigDecimal | None,
        Field(
            description="A pair of values representing the min and max values within this column."
        ),
    ] = None
    currency_format: Annotated[
        ApiCurrencyFormat | None,
        Field(
            alias="currencyFormat",
            description="Metadata on the detected number format of this column.",
        ),
    ] = None
    example_pair_from_currency_formatter: Annotated[
        list[str] | None,
        Field(
            alias="examplePairFromCurrencyFormatter",
            description="A pair of values as examples in the event that two or more unambiguous number formats are detected in the same column.",
        ),
    ] = None
    sum: Annotated[
        float | None,
        Field(
            description="The sum of all values in this column, up to a maximum of 10e<sup>50</sup>. Values smaller than 10e<sup>-50</sup> will be rounded up."
        ),
    ] = None
    capped_sum: Annotated[
        bool | None,
        Field(
            alias="cappedSum",
            description="If `true` then the sum is larger than 10e<sup>50</sup>.",
        ),
    ] = None
    capped_max: Annotated[
        bool | None,
        Field(
            alias="cappedMax",
            description="If `true` then at least one individual value is larger than 10e<sup>50</sup>.",
        ),
    ] = None


class ApiTableMetadata(BaseItem):
    cell_length_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="cellLengthMetrics",
            description="Metrics regarding cells that are larger than 2000 characters in the table.",
        ),
    ] = None
    density_metrics: Annotated[
        ApiDensityMetrics | None,
        Field(
            alias="densityMetrics", description="Metrics regarding whole table density."
        ),
    ] = None
    inconsistent_date_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="inconsistentDateMetrics",
            description="Metrics regarding inconsistent date formats within columns for the entire table.",
        ),
    ] = None
    null_value_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="nullValueMetrics",
            description="Metrics regarding “null” values across the entire table.",
        ),
    ] = None
    numeric_column_metrics: Annotated[
        ApiBasicMetrics | None,
        Field(
            alias="numericColumnMetrics",
            description="Metrics regarding numeric columns within the table.",
        ),
    ] = None
    overall_data_type_metrics: Annotated[
        ApiOverallDataTypeMetrics | None,
        Field(
            alias="overallDataTypeMetrics",
            description="Metrics regarding detected data types across the entire table.",
        ),
    ] = None
    scientific_notation_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="scientificNotationMetrics",
            description="Metrics regarding scientific notation across the entire table.",
        ),
    ] = None
    sheet_metrics: Annotated[
        ApiSheetMetrics | None,
        Field(
            alias="sheetMetrics",
            description="Metrics regarding excel sheets within the underlying excel file.",
        ),
    ] = None
    special_character_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="specialCharacterMetrics",
            description="Metrics regarding special characters across the entire table.",
        ),
    ] = None
    uneven_columns_metrics: Annotated[
        ApiHistogramMetrics | None,
        Field(
            alias="unevenColumnsMetrics",
            description="Metrics regarding column length by row.",
        ),
    ] = None


class ApiTextTypeDetails(BaseItem):
    range: Annotated[
        RangeInteger | None,
        Field(
            description="A pair of values representing the min and max length of text values within this column."
        ),
    ] = None


class ApiAnalysisSourceUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    warnings_ignored: Annotated[
        bool | None,
        Field(
            alias="warningsIgnored",
            description="Indicates whether or not warnings should be ignored.",
        ),
    ] = None
    target_workflow_state: Annotated[
        ApiAnalysisSourceUpdateTargetWorkflowState | None,
        Field(
            alias="targetWorkflowState",
            description="The state that the current workflow will advance to.",
        ),
    ] = None
    apply_degrouper: Annotated[
        bool | None,
        Field(
            alias="applyDegrouper",
            description="Indicates whether or not the degrouper should be applied.",
        ),
    ] = None
    proposed_column_mappings: Annotated[
        list[ApiProposedColumnMappingUpdate] | None,
        Field(
            alias="proposedColumnMappings",
            description="Details about the proposed column mapping.",
        ),
    ] = None
    column_mappings: Annotated[
        list[ApiColumnMappingUpdate] | None,
        Field(alias="columnMappings", description="Details about column mapping."),
    ] = None
    proposed_virtual_columns: Annotated[
        list[
            ApiProposedDuplicateVirtualColumnUpdate
            | ApiProposedJoinVirtualColumnUpdate
            | ApiProposedSplitByDelimiterVirtualColumnUpdate
            | ApiProposedSplitByPositionVirtualColumnUpdate
        ]
        | None,
        Field(
            alias="proposedVirtualColumns",
            description="Details about the proposed virtual columns added during the file import process.",
        ),
    ] = None
    virtual_columns: Annotated[
        list[
            ApiDuplicateVirtualColumnUpdate
            | ApiJoinVirtualColumnUpdate
            | ApiSplitByDelimiterVirtualColumnUpdate
            | ApiSplitByPositionVirtualColumnUpdate
        ]
        | None,
        Field(
            alias="virtualColumns",
            description="Details about the virtual columns added during file ingestion. ",
        ),
    ] = None
    proposed_ambiguous_column_resolutions: Annotated[
        list[ApiProposedAmbiguousColumnResolutionUpdate] | None,
        Field(
            alias="proposedAmbiguousColumnResolutions",
            description="Details about the virtual columns added during file ingestion.",
        ),
    ] = None
    ambiguous_column_resolutions: Annotated[
        list[ApiAmbiguousColumnUpdate] | None,
        Field(
            alias="ambiguousColumnResolutions",
            description="Details about resolutions to ambiguity in a column.",
        ),
    ] = None
    proposed_transaction_id_selection: Annotated[
        ApiTransactionIdSelectionUpdate | None,
        Field(
            alias="proposedTransactionIdSelection",
            description="The proposed columns to include when selecting a transaction ID.",
        ),
    ] = None
    transaction_id_selection: Annotated[
        ApiTransactionIdSelectionUpdate | None,
        Field(
            alias="transactionIdSelection",
            description="Details about transaction ID selection.",
        ),
    ] = None


class ApiPageApiWebhookRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiWebhookRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPageApiTransactionIdPreviewRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiTransactionIdPreviewRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiDataTypeMetricsRead(BaseItem):
    state: Annotated[
        ApiDataTypeMetricsReadState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreviewRead] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    non_null_value_count: Annotated[
        int | None,
        Field(
            alias="nonNullValueCount",
            description="The number of non-null values in this column.",
        ),
    ] = None
    type_counts: Annotated[
        dict[str, int] | None,
        Field(
            alias="typeCounts",
            description="A map of column type to number of occurrences. A single column value can match multiple types.",
        ),
    ] = None
    text_type_details: Annotated[
        ApiTextTypeDetailsRead | None,
        Field(
            alias="textTypeDetails",
            description="Metrics regarding the text type values in this column.",
        ),
    ] = None
    numeric_type_details: Annotated[
        ApiNumericTypeDetailsRead | None,
        Field(
            alias="numericTypeDetails",
            description="Metrics regarding the number type values in this column.",
        ),
    ] = None
    date_type_details: Annotated[
        ApiDateTypeDetailsRead | None,
        Field(
            alias="dateTypeDetails",
            description="Metrics regarding the date type values in this column.",
        ),
    ] = None
    detected_types: Annotated[
        list[ApiDataTypeMetricsReadDetectedType] | None,
        Field(
            alias="detectedTypes",
            description="A list of all detected types in this column.",
        ),
    ] = None
    dominant_type: Annotated[
        ApiDataTypeMetricsReadDominantType | None,
        Field(
            alias="dominantType",
            description="The type determined to be the most prevalent in this column.",
        ),
    ] = None


class ApiAnalysisSourceCreate(BaseItem):
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="Identifies the associated analysis."),
    ] = None
    analysis_period_id: Annotated[
        str | None,
        Field(
            alias="analysisPeriodId",
            description="Identifies the analysis period within MindBridge.",
        ),
    ] = None
    analysis_source_type_id: Annotated[
        str | None,
        Field(
            alias="analysisSourceTypeId",
            description="Identifies the analysis source type.",
        ),
    ] = None
    file_manager_file_id: Annotated[
        str | None,
        Field(
            alias="fileManagerFileId",
            deprecated=True,
            description="Identifies the specific file manager file within MindBridge.",
        ),
    ] = None
    additional_data_column_field: Annotated[
        str | None,
        Field(
            alias="additionalDataColumnField",
            description="When creating an additional data source type, this indicates which additional data column is being targeted.",
        ),
    ] = None
    warnings_ignored: Annotated[
        bool | None,
        Field(
            alias="warningsIgnored",
            description="Indicates whether or not warnings should be ignored.",
        ),
    ] = None
    target_workflow_state: Annotated[
        ApiAnalysisSourceCreateTargetWorkflowState | None,
        Field(
            alias="targetWorkflowState",
            description="The state that the current workflow will advance to.",
        ),
    ] = None
    apply_degrouper: Annotated[
        bool | None,
        Field(
            alias="applyDegrouper",
            description="Indicates whether or not the degrouper should be applied.",
        ),
    ] = None
    proposed_column_mappings: Annotated[
        list[ApiProposedColumnMappingCreate] | None,
        Field(
            alias="proposedColumnMappings",
            description="Details about the proposed column mapping.",
        ),
    ] = None
    proposed_virtual_columns: Annotated[
        list[
            ApiProposedDuplicateVirtualColumnCreate
            | ApiProposedJoinVirtualColumnCreate
            | ApiProposedSplitByDelimiterVirtualColumnCreate
            | ApiProposedSplitByPositionVirtualColumnCreate
        ]
        | None,
        Field(
            alias="proposedVirtualColumns",
            description="Details about the proposed virtual columns added during the file import process.",
        ),
    ] = None
    proposed_ambiguous_column_resolutions: Annotated[
        list[ApiProposedAmbiguousColumnResolutionCreate] | None,
        Field(
            alias="proposedAmbiguousColumnResolutions",
            description="Details about the virtual columns added during file ingestion.",
        ),
    ] = None
    proposed_transaction_id_selection: Annotated[
        ApiTransactionIdSelectionCreate | None,
        Field(
            alias="proposedTransactionIdSelection",
            description="The proposed columns to include when selecting a transaction ID.",
        ),
    ] = None


class ApiDataTypeMetrics(BaseItem):
    state: Annotated[
        ApiDataTypeMetricsState | None,
        Field(description="Validation state of the metric within its context."),
    ] = None
    data_previews: Annotated[
        list[ApiDataPreview] | None,
        Field(
            alias="dataPreviews",
            description="A list of values within the table relevant to the metric.",
        ),
    ] = None
    non_null_value_count: Annotated[
        int | None,
        Field(
            alias="nonNullValueCount",
            description="The number of non-null values in this column.",
        ),
    ] = None
    type_counts: Annotated[
        dict[str, int] | None,
        Field(
            alias="typeCounts",
            description="A map of column type to number of occurrences. A single column value can match multiple types.",
        ),
    ] = None
    text_type_details: Annotated[
        ApiTextTypeDetails | None,
        Field(
            alias="textTypeDetails",
            description="Metrics regarding the text type values in this column.",
        ),
    ] = None
    numeric_type_details: Annotated[
        ApiNumericTypeDetails | None,
        Field(
            alias="numericTypeDetails",
            description="Metrics regarding the number type values in this column.",
        ),
    ] = None
    date_type_details: Annotated[
        ApiDateTypeDetails | None,
        Field(
            alias="dateTypeDetails",
            description="Metrics regarding the date type values in this column.",
        ),
    ] = None
    detected_types: Annotated[
        list[ApiDataTypeMetricsDetectedType] | None,
        Field(
            alias="detectedTypes",
            description="A list of all detected types in this column.",
        ),
    ] = None
    dominant_type: Annotated[
        ApiDataTypeMetricsDominantType | None,
        Field(
            alias="dominantType",
            description="The type determined to be the most prevalent in this column.",
        ),
    ] = None


class ApiColumnMetadataRead(BaseItem):
    cell_length_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="cellLengthMetrics",
            description="Metrics regarding cells that are larger than 2000 characters in the column.",
        ),
    ] = None
    data_type_metrics: Annotated[
        ApiDataTypeMetricsRead | None,
        Field(
            alias="dataTypeMetrics",
            description="Metrics regarding the data types of column values.",
        ),
    ] = None
    density_metrics: Annotated[
        ApiDensityMetricsRead | None,
        Field(
            alias="densityMetrics",
            description="Metrics regarding the density of column values.",
        ),
    ] = None
    distinct_value_metrics: Annotated[
        ApiDistinctValueMetricsRead | None,
        Field(
            alias="distinctValueMetrics",
            description="Metrics regarding the uniqueness of column values.",
        ),
    ] = None
    null_value_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="nullValueMetrics",
            description="Metrics regarding “null” values in the column.",
        ),
    ] = None
    scientific_notation_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="scientificNotationMetrics",
            description="Metrics regarding the use of scientific notation in the column.",
        ),
    ] = None
    special_character_metrics: Annotated[
        ApiCountMetricsRead | None,
        Field(
            alias="specialCharacterMetrics",
            description="Metrics regarding the use of special characters in the column.",
        ),
    ] = None


class ApiColumnMetadata(BaseItem):
    cell_length_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="cellLengthMetrics",
            description="Metrics regarding cells that are larger than 2000 characters in the column.",
        ),
    ] = None
    data_type_metrics: Annotated[
        ApiDataTypeMetrics | None,
        Field(
            alias="dataTypeMetrics",
            description="Metrics regarding the data types of column values.",
        ),
    ] = None
    density_metrics: Annotated[
        ApiDensityMetrics | None,
        Field(
            alias="densityMetrics",
            description="Metrics regarding the density of column values.",
        ),
    ] = None
    distinct_value_metrics: Annotated[
        ApiDistinctValueMetrics | None,
        Field(
            alias="distinctValueMetrics",
            description="Metrics regarding the uniqueness of column values.",
        ),
    ] = None
    null_value_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="nullValueMetrics",
            description="Metrics regarding “null” values in the column.",
        ),
    ] = None
    scientific_notation_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="scientificNotationMetrics",
            description="Metrics regarding the use of scientific notation in the column.",
        ),
    ] = None
    special_character_metrics: Annotated[
        ApiCountMetrics | None,
        Field(
            alias="specialCharacterMetrics",
            description="Metrics regarding the use of special characters in the column.",
        ),
    ] = None


class ApiColumnDataRead(BaseItem):
    column_name: Annotated[
        str | None, Field(alias="columnName", description="The name of the column.")
    ] = None
    position: Annotated[int | None, Field(description="The index of the column.")] = (
        None
    )
    synthetic: Annotated[
        bool | None,
        Field(
            description="If `true` this column was generated, as opposed to being a part of the original data."
        ),
    ] = None
    row_sample: Annotated[
        list[str] | None,
        Field(
            alias="rowSample",
            description="A list of values from this column across multiple rows. All values are distinct.",
        ),
    ] = None
    column_metadata: Annotated[
        ApiColumnMetadataRead | None,
        Field(alias="columnMetadata", description="A collection of metrics."),
    ] = None


class ApiTabularFileInfoRead(ApiFileInfoRead, ApiFileInfo):
    header_row_index: Annotated[
        int | None,
        Field(
            alias="headerRowIndex",
            description="The row number of the first detected header.",
        ),
    ] = None
    first_line: Annotated[
        str | None, Field(alias="firstLine", description="The first line of the table.")
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The delimiter character used to separate cells. Only populated when the underlying file is a CSV file."
        ),
    ] = None
    last_non_blank_row_index: Annotated[
        int | None,
        Field(
            alias="lastNonBlankRowIndex",
            description="The row number of the last row that isn't blank.",
        ),
    ] = None
    table_metadata: Annotated[
        ApiTableMetadataRead | None,
        Field(
            alias="tableMetadata",
            description="A collection of metadata describing the table as a whole.",
        ),
    ] = None
    column_data: Annotated[
        list[ApiColumnDataRead] | None,
        Field(
            alias="columnData",
            description="A list of column metadata entities, describing each column.",
        ),
    ] = None
    row_content_snippets: Annotated[
        list[list[str]] | None,
        Field(
            alias="rowContentSnippets",
            description="A list of sample rows from the underlying file.",
        ),
    ] = None
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiAnalysisSourceRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId", description="Identifies the associated engagement."
        ),
    ] = None
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="Identifies the associated analysis."),
    ] = None
    analysis_period_id: Annotated[
        str | None,
        Field(
            alias="analysisPeriodId",
            description="Identifies the analysis period within MindBridge.",
        ),
    ] = None
    analysis_source_type_id: Annotated[
        str | None,
        Field(
            alias="analysisSourceTypeId",
            description="Identifies the analysis source type.",
        ),
    ] = None
    file_manager_file_id: Annotated[
        str | None,
        Field(
            alias="fileManagerFileId",
            deprecated=True,
            description="Identifies the specific file manager file within MindBridge.",
        ),
    ] = None
    additional_data_column_field: Annotated[
        str | None,
        Field(
            alias="additionalDataColumnField",
            description="When creating an additional data source type, this indicates which additional data column is being targeted.",
        ),
    ] = None
    warnings_ignored: Annotated[
        bool | None,
        Field(
            alias="warningsIgnored",
            description="Indicates whether or not warnings should be ignored.",
        ),
    ] = None
    warnings: Annotated[
        list[ApiMessageRead] | None,
        Field(description="Details about the warnings associated with the source."),
    ] = None
    errors: Annotated[
        list[ApiMessageRead] | None,
        Field(
            description="Details about the errors associated with the specific source."
        ),
    ] = None
    workflow_state: Annotated[
        ApiAnalysisSourceReadWorkflowState | None,
        Field(alias="workflowState", description="The current state of the workflow."),
    ] = None
    target_workflow_state: Annotated[
        ApiAnalysisSourceReadTargetWorkflowState | None,
        Field(
            alias="targetWorkflowState",
            description="The state that the current workflow will advance to.",
        ),
    ] = None
    detected_format: Annotated[
        ApiAnalysisSourceReadDetectedFormat | None,
        Field(
            alias="detectedFormat",
            description="The data format that MindBridge detected.",
        ),
    ] = None
    apply_degrouper: Annotated[
        bool | None,
        Field(
            alias="applyDegrouper",
            description="Indicates whether or not the degrouper should be applied.",
        ),
    ] = None
    degrouper_applied: Annotated[
        bool | None,
        Field(
            alias="degrouperApplied",
            description="Indicates whether or not the degrouper was applied.",
        ),
    ] = None
    file_info: Annotated[
        ApiTabularFileInfoRead | None,
        Field(
            alias="fileInfo",
            description="Details about the file being imported into MindBridge.",
        ),
    ] = None
    proposed_column_mappings: Annotated[
        list[ApiProposedColumnMappingRead] | None,
        Field(
            alias="proposedColumnMappings",
            description="Details about the proposed column mapping.",
        ),
    ] = None
    column_mappings: Annotated[
        list[ApiColumnMappingRead] | None,
        Field(alias="columnMappings", description="Details about column mapping."),
    ] = None
    proposed_virtual_columns: Annotated[
        list[
            ApiProposedDuplicateVirtualColumnRead
            | ApiProposedJoinVirtualColumnRead
            | ApiProposedSplitByDelimiterVirtualColumnRead
            | ApiProposedSplitByPositionVirtualColumnRead
        ]
        | None,
        Field(
            alias="proposedVirtualColumns",
            description="Details about the proposed virtual columns added during the file import process.",
        ),
    ] = None
    virtual_columns: Annotated[
        list[
            ApiDuplicateVirtualColumnRead
            | ApiJoinVirtualColumnRead
            | ApiSplitByDelimiterVirtualColumnRead
            | ApiSplitByPositionVirtualColumnRead
        ]
        | None,
        Field(
            alias="virtualColumns",
            description="Details about the virtual columns added during file ingestion. ",
        ),
    ] = None
    proposed_ambiguous_column_resolutions: Annotated[
        list[ApiProposedAmbiguousColumnResolutionRead] | None,
        Field(
            alias="proposedAmbiguousColumnResolutions",
            description="Details about the virtual columns added during file ingestion.",
        ),
    ] = None
    ambiguous_column_resolutions: Annotated[
        list[ApiAmbiguousColumnRead] | None,
        Field(
            alias="ambiguousColumnResolutions",
            description="Details about resolutions to ambiguity in a column.",
        ),
    ] = None
    proposed_transaction_id_selection: Annotated[
        ApiTransactionIdSelectionRead | None,
        Field(
            alias="proposedTransactionIdSelection",
            description="The proposed columns to include when selecting a transaction ID.",
        ),
    ] = None
    transaction_id_selection: Annotated[
        ApiTransactionIdSelectionRead | None,
        Field(
            alias="transactionIdSelection",
            description="Details about transaction ID selection.",
        ),
    ] = None
    file_info_versions: Annotated[
        dict[str, str] | None,
        Field(
            alias="fileInfoVersions",
            description="A map of providing a set of file info IDs by their Analysis Source File Version.",
        ),
    ] = None
    file_manager_files: Annotated[
        dict[str, str] | None,
        Field(
            alias="fileManagerFiles",
            description="A map of providing a set of file manager file IDs by their Analysis Source File Version.",
        ),
    ] = None


class ApiPageApiAnalysisSourceRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiAnalysisSourceRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiColumnData(BaseItem):
    column_name: Annotated[
        str | None, Field(alias="columnName", description="The name of the column.")
    ] = None
    position: Annotated[int | None, Field(description="The index of the column.")] = (
        None
    )
    synthetic: Annotated[
        bool | None,
        Field(
            description="If `true` this column was generated, as opposed to being a part of the original data."
        ),
    ] = None
    row_sample: Annotated[
        list[str] | None,
        Field(
            alias="rowSample",
            description="A list of values from this column across multiple rows. All values are distinct.",
        ),
    ] = None
    column_metadata: Annotated[
        ApiColumnMetadata | None,
        Field(alias="columnMetadata", description="A collection of metrics."),
    ] = None


class ApiTabularFileInfo(ApiFileInfo):
    header_row_index: Annotated[
        int | None,
        Field(
            alias="headerRowIndex",
            description="The row number of the first detected header.",
        ),
    ] = None
    first_line: Annotated[
        str | None, Field(alias="firstLine", description="The first line of the table.")
    ] = None
    delimiter: Annotated[
        str | None,
        Field(
            description="The delimiter character used to separate cells. Only populated when the underlying file is a CSV file."
        ),
    ] = None
    last_non_blank_row_index: Annotated[
        int | None,
        Field(
            alias="lastNonBlankRowIndex",
            description="The row number of the last row that isn't blank.",
        ),
    ] = None
    table_metadata: Annotated[
        ApiTableMetadata | None,
        Field(
            alias="tableMetadata",
            description="A collection of metadata describing the table as a whole.",
        ),
    ] = None
    column_data: Annotated[
        list[ApiColumnData] | None,
        Field(
            alias="columnData",
            description="A list of column metadata entities, describing each column.",
        ),
    ] = None
    row_content_snippets: Annotated[
        list[list[str]] | None,
        Field(
            alias="rowContentSnippets",
            description="A list of sample rows from the underlying file.",
        ),
    ] = None
    version: Annotated[
        int, Field(description="Data integrity version to ensure data consistency.")
    ]


class ApiPageApiFileInfoRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiTabularFileInfoRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiFilterGroupConditionApiFilterGroupCondition13(BaseItem):
    type: Annotated[
        Literal["GROUP"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "GROUP"
    operator: Annotated[
        ApiFilterGroupConditionOperator | None,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ] = None
    conditions: Annotated[
        list[ApiFilterCondition] | None,
        Field(description="The entries within this condition group.", min_length=1),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13(BaseItem):
    type: Annotated[
        Literal["GROUP"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "GROUP"
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator | None,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ] = None
    conditions: Annotated[
        list[ApiFilterCondition] | None,
        Field(description="The entries within this condition group.", min_length=1),
    ] = None


class ApiFilterUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    filter_type: Annotated[
        ApiFilterUpdateFilterType | None,
        Field(
            alias="filterType",
            description="The type of this filter. Determines in which context analyses can access it.",
            title="Filter Type",
        ),
    ] = None
    name: Annotated[
        dict[str, str] | None, Field(description="The name of this filter.")
    ] = None
    category: Annotated[
        dict[str, str] | None, Field(description="The category of this filter.")
    ] = None
    display_currency_code: Annotated[
        str | None,
        Field(
            alias="displayCurrencyCode",
            description="The ISO 4217 3 digit currency code used to determine how currency values are formatted for display. Defaults to `USD` if no value is selected.",
        ),
    ] = None
    display_locale: Annotated[
        str | None,
        Field(
            alias="displayLocale",
            description="The ISO 639 locale identifier used when formatting some display values. Defaults to `en-us` if no value is specified.",
        ),
    ] = None
    condition: Annotated[
        ApiFilterGroupConditionUpdate | None,
        Field(
            description="A group filter containing all the conditions included in this filter."
        ),
    ] = None


class ApiFilterGroupConditionReadApiFilterGroupConditionRead13(BaseItem):
    type: Annotated[
        Literal["GROUP"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "GROUP"
    operator: Annotated[
        ApiFilterGroupConditionReadOperator | None,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ] = None
    conditions: Annotated[
        list[ApiFilterCondition] | None,
        Field(description="The entries within this condition group.", min_length=1),
    ] = None


class ApiFilterRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(description="Data integrity version to ensure data consistency."),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    analysis_type_id: Annotated[
        str | None,
        Field(
            alias="analysisTypeId",
            description="Identifies the associated analysis type.",
        ),
    ] = None
    organization_id: Annotated[
        str | None,
        Field(
            alias="organizationId",
            description="Identifies the parent organization, if applicable. Can only be set if `filterType` is `ORGANIZATION` or `PRIVATE`.",
        ),
    ] = None
    library_id: Annotated[
        str | None,
        Field(
            alias="libraryId",
            description="Identifies the parent library, if applicable. Can only be set if `filterType` is `LIBRARY`.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="Identifies the parent engagement, if applicable. Can only be set if `filterType` is `ENGAGEMENT`.",
        ),
    ] = None
    filter_type: Annotated[
        ApiFilterReadFilterType | None,
        Field(
            alias="filterType",
            description="The type of this filter. Determines in which context analyses can access it.",
            title="Filter Type",
        ),
    ] = None
    data_type: Annotated[
        ApiFilterReadDataType | None,
        Field(
            alias="dataType",
            description="The intended data type for this filter.",
            title="Filter Data Type",
        ),
    ] = None
    name: Annotated[
        dict[str, str] | None, Field(description="The name of this filter.")
    ] = None
    category: Annotated[
        dict[str, str] | None, Field(description="The category of this filter.")
    ] = None
    display_currency_code: Annotated[
        str | None,
        Field(
            alias="displayCurrencyCode",
            description="The ISO 4217 3 digit currency code used to determine how currency values are formatted for display. Defaults to `USD` if no value is selected.",
        ),
    ] = None
    display_locale: Annotated[
        str | None,
        Field(
            alias="displayLocale",
            description="The ISO 639 locale identifier used when formatting some display values. Defaults to `en-us` if no value is specified.",
        ),
    ] = None
    condition: Annotated[
        ApiFilterGroupConditionRead | None,
        Field(
            description="A group filter containing all the conditions included in this filter."
        ),
    ] = None
    legacy_filter_format: Annotated[
        bool | None,
        Field(
            alias="legacyFilterFormat",
            description="If `true` this filter is saved in a legacy format that can't be represented in the API.",
        ),
    ] = None


class ApiPopulationTagUpdate(BaseItem):
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the population.", max_length=80, min_length=0),
    ] = None
    category: Annotated[
        str | None,
        Field(
            description="The category of the population.", max_length=80, min_length=0
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            description="A description of the population.", max_length=250, min_length=0
        ),
    ] = None
    reason_for_change: Annotated[
        str | None,
        Field(
            alias="reasonForChange",
            description="The reason for the latest change made to the population.",
            max_length=250,
            min_length=0,
        ),
    ] = None
    disabled: bool | None = None
    condition: Annotated[
        ApiFilterGroupConditionUpdate | None,
        Field(
            description="The filter condition used to determine which entries are included in the population."
        ),
    ] = None
    display_currency_code: Annotated[
        str | None,
        Field(
            alias="displayCurrencyCode",
            description="The ISO 4217 three-digit currency code that determines how currency values are formatted. Defaults to `USD` if not specified.",
        ),
    ] = None
    display_locale: Annotated[
        str | None,
        Field(
            alias="displayLocale",
            description="The ISO 639 locale identifier used to format display values. Defaults to `en-us` if not specified.",
        ),
    ] = None


class ApiPopulationTagRead(BaseItem):
    id: Annotated[str | None, Field(description="The unique object identifier.")] = None
    version: Annotated[
        int | None,
        Field(
            description="Indicates the data integrity version to ensure data consistency."
        ),
    ] = None
    creation_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="creationDate",
            description="The date that the object was originally created.",
        ),
    ] = None
    last_modified_date: Annotated[
        AwareDatetime | None,
        Field(
            alias="lastModifiedDate",
            description="The date that the object was last updated or modified.",
        ),
    ] = None
    created_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="createdUserInfo",
            description="Details about the user who created the object.",
        ),
    ] = None
    last_modified_user_info: Annotated[
        ApiUserInfoRead | None,
        Field(
            alias="lastModifiedUserInfo",
            description="Details about the user who last modified or updated the object.",
        ),
    ] = None
    analysis_type_id: Annotated[str | None, Field(alias="analysisTypeId")] = None
    library_id: Annotated[
        str | None,
        Field(alias="libraryId", description="The ID of the parent library."),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(alias="engagementId", description="The ID of the parent engagement."),
    ] = None
    derived_from_library: Annotated[
        bool | None,
        Field(
            alias="derivedFromLibrary",
            description="Indicates that the engagement population was derived from a library.",
        ),
    ] = None
    disabled_for_analysis_ids: Annotated[
        list[str] | None,
        Field(
            alias="disabledForAnalysisIds",
            description="Lists the analysis IDs where the engagement population is disabled.",
        ),
    ] = None
    promoted_from_analysis_id: Annotated[
        str | None,
        Field(
            alias="promotedFromAnalysisId",
            description="Identifies the analysis from which the engagement population was promoted.",
        ),
    ] = None
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="The ID of the parent analysis."),
    ] = None
    derived_from_engagement: Annotated[
        bool | None,
        Field(
            alias="derivedFromEngagement",
            description="Indicates whether the analysis population was derived from an engagement.",
        ),
    ] = None
    base_population_id: Annotated[
        str | None,
        Field(
            alias="basePopulationId",
            description="The ID of the population the current population is based on.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the population.", max_length=80, min_length=0),
    ] = None
    category: Annotated[
        str | None,
        Field(
            description="The category of the population.", max_length=80, min_length=0
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            description="A description of the population.", max_length=250, min_length=0
        ),
    ] = None
    cloned_from: Annotated[
        str | None,
        Field(
            alias="clonedFrom",
            description="Identifies the population the current population was cloned from.",
        ),
    ] = None
    reason_for_change: Annotated[
        str | None,
        Field(
            alias="reasonForChange",
            description="The reason for the latest change made to the population.",
            max_length=250,
            min_length=0,
        ),
    ] = None
    disabled: bool | None = None
    condition: Annotated[
        ApiFilterGroupConditionRead | None,
        Field(
            description="The filter condition used to determine which entries are included in the population."
        ),
    ] = None
    legacy_filter_format: Annotated[
        bool | None,
        Field(
            alias="legacyFilterFormat",
            description="If `true`, this population uses a legacy filter format that cannot be represented in the current condition format.",
        ),
    ] = None
    display_currency_code: Annotated[
        str | None,
        Field(
            alias="displayCurrencyCode",
            description="The ISO 4217 three-digit currency code that determines how currency values are formatted. Defaults to `USD` if not specified.",
        ),
    ] = None
    display_locale: Annotated[
        str | None,
        Field(
            alias="displayLocale",
            description="The ISO 639 locale identifier used to format display values. Defaults to `en-us` if not specified.",
        ),
    ] = None


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13(BaseItem):
    type: Annotated[
        Literal["GROUP"] | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = "GROUP"
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator | None,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ] = None
    conditions: Annotated[
        list[ApiFilterCondition] | None,
        Field(description="The entries within this condition group.", min_length=1),
    ] = None


class ApiFilterCreate(BaseItem):
    analysis_type_id: Annotated[
        str | None,
        Field(
            alias="analysisTypeId",
            description="Identifies the associated analysis type.",
        ),
    ] = None
    organization_id: Annotated[
        str | None,
        Field(
            alias="organizationId",
            description="Identifies the parent organization, if applicable. Can only be set if `filterType` is `ORGANIZATION` or `PRIVATE`.",
        ),
    ] = None
    library_id: Annotated[
        str | None,
        Field(
            alias="libraryId",
            description="Identifies the parent library, if applicable. Can only be set if `filterType` is `LIBRARY`.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="Identifies the parent engagement, if applicable. Can only be set if `filterType` is `ENGAGEMENT`.",
        ),
    ] = None
    filter_type: Annotated[
        ApiFilterCreateFilterType | None,
        Field(
            alias="filterType",
            description="The type of this filter. Determines in which context analyses can access it.",
            title="Filter Type",
        ),
    ] = None
    data_type: Annotated[
        ApiFilterCreateDataType | None,
        Field(
            alias="dataType",
            description="The intended data type for this filter.",
            title="Filter Data Type",
        ),
    ] = None
    name: Annotated[
        dict[str, str] | None, Field(description="The name of this filter.")
    ] = None
    category: Annotated[
        dict[str, str] | None, Field(description="The category of this filter.")
    ] = None
    display_currency_code: Annotated[
        str | None,
        Field(
            alias="displayCurrencyCode",
            description="The ISO 4217 3 digit currency code used to determine how currency values are formatted for display. Defaults to `USD` if no value is selected.",
        ),
    ] = None
    display_locale: Annotated[
        str | None,
        Field(
            alias="displayLocale",
            description="The ISO 639 locale identifier used when formatting some display values. Defaults to `en-us` if no value is specified.",
        ),
    ] = None
    condition: Annotated[
        ApiFilterGroupConditionCreate | None,
        Field(
            description="A group filter containing all the conditions included in this filter."
        ),
    ] = None


class ApiPageApiFilterRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiFilterRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiPopulationTagCreate(BaseItem):
    analysis_type_id: Annotated[str | None, Field(alias="analysisTypeId")] = None
    library_id: Annotated[
        str | None,
        Field(alias="libraryId", description="The ID of the parent library."),
    ] = None
    analysis_id: Annotated[
        str | None,
        Field(alias="analysisId", description="The ID of the parent analysis."),
    ] = None
    base_population_id: Annotated[
        str | None,
        Field(
            alias="basePopulationId",
            description="The ID of the population the current population is based on.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name of the population.", max_length=80, min_length=0),
    ] = None
    category: Annotated[
        str | None,
        Field(
            description="The category of the population.", max_length=80, min_length=0
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            description="A description of the population.", max_length=250, min_length=0
        ),
    ] = None
    disabled: bool | None = None
    condition: Annotated[
        ApiFilterGroupConditionCreate | None,
        Field(
            description="The filter condition used to determine which entries are included in the population."
        ),
    ] = None
    display_currency_code: Annotated[
        str | None,
        Field(
            alias="displayCurrencyCode",
            description="The ISO 4217 three-digit currency code that determines how currency values are formatted. Defaults to `USD` if not specified.",
        ),
    ] = None
    display_locale: Annotated[
        str | None,
        Field(
            alias="displayLocale",
            description="The ISO 639 locale identifier used to format display values. Defaults to `en-us` if not specified.",
        ),
    ] = None


class ApiPageApiPopulationTagRead(BaseItem):
    page_number: Annotated[int | None, Field(alias="pageNumber")] = None
    total_pages: Annotated[int | None, Field(alias="totalPages")] = None
    content: list[ApiPopulationTagRead] | None = None
    number_of_elements: Annotated[int | None, Field(alias="numberOfElements")] = None
    total_elements: Annotated[int | None, Field(alias="totalElements")] = None
    pageable: Annotated[ApiPageableRead | None, Field(deprecated=True)] = None
    page_size: Annotated[int | None, Field(alias="pageSize", deprecated=True)] = None
    sort: Annotated[SortnullRead | None, Field(deprecated=True)] = None
    first: Annotated[bool | None, Field(deprecated=True)] = None
    last: Annotated[bool | None, Field(deprecated=True)] = None
    size: Annotated[int | None, Field(deprecated=True)] = None
    number: Annotated[int | None, Field(deprecated=True)] = None


class ApiDataTableExportToFileManagerRequestCreate(BaseItem):
    data_table_id: Annotated[
        str | None,
        Field(
            alias="dataTableId",
            description="The ID of the Data Table to export data from.",
        ),
    ] = None
    engagement_id: Annotated[
        str | None,
        Field(
            alias="engagementId",
            description="The engagement that the Data Table belongs to.",
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(description="The name for the exported CSV file without extension."),
    ] = None
    parent_file_manager_entity_id: Annotated[
        str | None,
        Field(
            alias="parentFileManagerEntityId",
            description="The ID of the File Manager directory to place the exported file in. If null, the file is placed in the engagement's root directory.",
        ),
    ] = None
    query: Annotated[
        MindBridgeQueryTerm | None,
        Field(description="An optional filter to apply to the data before exporting."),
    ] = None
    sort: Annotated[
        ApiDataTableQuerySortOrderCreate | None,
        Field(description="An optional sort order to apply to the exported rows."),
    ] = None
    fields: Annotated[
        list[str] | None,
        Field(
            description="The list of field names (columns) to include in the export."
        ),
    ] = None
    limit: Annotated[
        int | None, Field(description="The maximum number of rows to export.", ge=1)
    ] = None
    csv_configuration: Annotated[
        ApiCsvConfigurationCreate | None,
        Field(
            alias="csvConfiguration",
            description="The configuration to use when generating the CSV file.",
        ),
    ] = None
    inner_list_csv_configuration: Annotated[
        ApiCsvConfigurationCreate | None,
        Field(
            alias="innerListCsvConfiguration",
            description="The configuration to use when formatting list values within cells in the CSV file.",
        ),
    ] = None


class ApiDataTableExportRequest(BaseItem):
    query: Annotated[
        MindBridgeQueryTerm | None,
        Field(
            description="The MindBridge QL query used to filter data in the data table."
        ),
    ] = None
    sort: Annotated[
        ApiDataTableQuerySortOrder | None,
        Field(
            description="Indicates how the data will be sorted.\n\nDefault sort order = ascending"
        ),
    ] = None
    fields: Annotated[
        list[str] | None,
        Field(description="The data table fields to be included in the results."),
    ] = None
    limit: Annotated[
        int | None, Field(description="The number of results to be returned.", ge=1)
    ] = None
    csv_configuration: Annotated[
        ApiCsvConfiguration | None,
        Field(
            alias="csvConfiguration",
            description="The configuration to use when generating the CSV file.",
        ),
    ] = None
    inner_list_csv_configuration: Annotated[
        ApiCsvConfiguration | None,
        Field(
            alias="innerListCsvConfiguration",
            description="The configuration to use when formatting lists within cells in the CSV file.",
        ),
    ] = None


class ApiDataTableQueryRead(BaseItem):
    query: Annotated[
        MindBridgeQueryTerm | None,
        Field(
            description="The MindBridge QL query used to filter data in the data table."
        ),
    ] = None
    page: Annotated[
        int | None,
        Field(
            description="The specific page of results. This operates on a zero-based page index (0..N).",
            ge=0,
        ),
    ] = None
    page_size: Annotated[
        int | None,
        Field(
            alias="pageSize",
            description="The number of results to be returned on each page.",
            ge=1,
            le=100,
        ),
    ] = None
    sort: Annotated[
        ApiDataTableQuerySortOrderRead | None,
        Field(
            description="Indicates how the data will be sorted.\n\nDefault sort order = ascending"
        ),
    ] = None
    fields: Annotated[
        list[str] | None,
        Field(description="The data table fields to be included in the results."),
    ] = None
    exclude_fields: Annotated[list[str] | None, Field(alias="excludeFields")] = None


class MindBridgeQueryTermMindBridgeQueryTerm14(BaseItem):
    field_and: Annotated[list[MindBridgeQueryTerm] | None, Field(alias="$and")] = None


class MindBridgeQueryTermMindBridgeQueryTerm15(BaseItem):
    field_or: Annotated[list[MindBridgeQueryTerm] | None, Field(alias="$or")] = None


MindBridgeQueryTerm = RootModel[
    dict[str, int | float | bool | str]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm1]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm2]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm3]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm4]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm5]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm6]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm8]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm9]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm10]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm11]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm12]
    | dict[str, MindBridgeQueryTermMindBridgeQueryTerm13]
    | MindBridgeQueryTermMindBridgeQueryTerm14
    | MindBridgeQueryTermMindBridgeQueryTerm15
    | MindBridgeQueryTermMindBridgeQueryTerm16
    | MindBridgeQueryTermMindBridgeQueryTerm17
    | dict[str, Any]
    | None
]


ApiFilterDateRangeCondition = RootModel[
    "ApiFilterDateRangeConditionApiFilterDateRangeCondition2"
]


ApiFilterDateValueCondition = RootModel[
    "ApiFilterDateValueConditionApiFilterDateValueCondition2"
]


class ApiFilterDateRangeConditionApiFilterDateRangeCondition2(
    ApiFilterDateRangeConditionApiFilterDateRangeCondition
):
    date_type: Annotated[
        Literal["BETWEEN"], Field(alias="dateType", title="Filter Date Type")
    ]
    field: str
    negated: bool
    range_end: Annotated[
        date,
        Field(
            alias="rangeEnd",
            description="The end of an ISO date range to compare entries to.",
        ),
    ]
    range_start: Annotated[
        date,
        Field(
            alias="rangeStart",
            description="The start of an ISO date range to compare entries to.",
        ),
    ]
    type: Annotated[Literal["DATE"], Field(title="Filter Condition Type")]


class ApiFilterDateValueConditionApiFilterDateValueCondition2(
    ApiFilterDateValueConditionApiFilterDateValueCondition
):
    date_type: Annotated[
        ApiFilterDateValueConditionDateType,
        Field(alias="dateType", title="Filter Date Type"),
    ]
    field: str
    negated: bool
    type: Annotated[Literal["DATE"], Field(title="Filter Condition Type")]
    value: Annotated[
        date, Field(description="An ISO date value to compare entries to.")
    ]


ApiFilterMaterialityOptionCondition = RootModel[
    "ApiFilterMaterialityOptionConditionApiFilterMaterialityOptionCondition1"
]


ApiFilterMaterialityValueCondition = RootModel[
    "ApiFilterMaterialityValueConditionApiFilterMaterialityValueCondition1"
]


class ApiFilterMaterialityOptionConditionApiFilterMaterialityOptionCondition1(
    ApiFilterMaterialityOptionConditionApiFilterMaterialityOptionCondition
):
    field: str
    materiality_option: Annotated[
        ApiFilterMaterialityOptionConditionMaterialityOption,
        Field(alias="materialityOption", title="Filter Materiality Value Options"),
    ]
    negated: bool
    type: Annotated[Literal["MATERIALITY"], Field(title="Filter Condition Type")]


class ApiFilterMaterialityValueConditionApiFilterMaterialityValueCondition1(
    ApiFilterMaterialityValueConditionApiFilterMaterialityValueCondition
):
    field: str
    materiality_option: Annotated[
        Literal["PERCENTAGE"],
        Field(alias="materialityOption", title="Filter Materiality Value Options"),
    ]
    negated: bool
    type: Annotated[Literal["MATERIALITY"], Field(title="Filter Condition Type")]
    value: Annotated[
        float,
        Field(
            description="The percentage value, as a decimal number, with 100.00 being 100%."
        ),
    ]


ApiFilterMonetaryValueRangeCondition = RootModel[
    "ApiFilterMonetaryValueRangeConditionApiFilterMonetaryValueRangeCondition2"
]


ApiFilterMonetaryValueValueCondition = RootModel[
    "ApiFilterMonetaryValueValueConditionApiFilterMonetaryValueValueCondition2"
]


class ApiFilterMonetaryValueRangeConditionApiFilterMonetaryValueRangeCondition2(
    ApiFilterMonetaryValueRangeConditionApiFilterMonetaryValueRangeCondition
):
    field: str
    monetary_value_type: Annotated[
        Literal["BETWEEN"],
        Field(alias="monetaryValueType", title="Filter Monetary Type"),
    ]
    negated: bool
    range_end: Annotated[
        int,
        Field(
            alias="rangeEnd",
            description="The end of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ]
    range_start: Annotated[
        int,
        Field(
            alias="rangeStart",
            description="The start of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ]
    type: Annotated[Literal["MONEY"], Field(title="Filter Condition Type")]


class ApiFilterMonetaryValueValueConditionApiFilterMonetaryValueValueCondition2(
    ApiFilterMonetaryValueValueConditionApiFilterMonetaryValueValueCondition
):
    field: str
    monetary_value_type: Annotated[
        ApiFilterMonetaryValueValueConditionMonetaryValueType,
        Field(alias="monetaryValueType", title="Filter Monetary Type"),
    ]
    negated: bool
    type: Annotated[Literal["MONEY"], Field(title="Filter Condition Type")]
    value: Annotated[
        int,
        Field(description="The MONEY_100 formatted number to compare with entries."),
    ]


ApiFilterNumericalValueRangeCondition = RootModel[
    "ApiFilterNumericalValueRangeConditionApiFilterNumericalValueRangeCondition2"
]


ApiFilterNumericalValueValueCondition = RootModel[
    "ApiFilterNumericalValueValueConditionApiFilterNumericalValueValueCondition2"
]


class ApiFilterNumericalValueRangeConditionApiFilterNumericalValueRangeCondition2(
    ApiFilterNumericalValueRangeConditionApiFilterNumericalValueRangeCondition
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal["BETWEEN"],
        Field(alias="numericalValueType", title="Filter Numerical Value Type"),
    ]
    range_end: Annotated[
        int,
        Field(
            alias="rangeEnd",
            description="The end value of a range to compare entries to.",
        ),
    ]
    range_start: Annotated[
        int,
        Field(
            alias="rangeStart",
            description="The start value of a range to compare entries to.",
        ),
    ]
    type: Annotated[Literal["NUMERICAL"], Field(title="Filter Condition Type")]


class ApiFilterNumericalValueValueConditionApiFilterNumericalValueValueCondition2(
    ApiFilterNumericalValueValueConditionApiFilterNumericalValueValueCondition
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        ApiFilterNumericalValueValueConditionNumericalValueType,
        Field(alias="numericalValueType", title="Filter Numerical Value Type"),
    ]
    type: Annotated[Literal["NUMERICAL"], Field(title="Filter Condition Type")]
    value: Annotated[int, Field(description="A value to compare entries to.")]


ApiFilterRiskScoreHMLCondition = RootModel[
    "ApiFilterRiskScoreHMLConditionApiFilterRiskScoreHMLCondition1"
]


ApiFilterRiskScorePercentCondition = RootModel[
    "ApiFilterRiskScorePercentConditionApiFilterRiskScorePercentCondition1"
]


class ApiFilterRiskScoreHMLConditionApiFilterRiskScoreHMLCondition1(
    ApiFilterRiskScoreHMLConditionApiFilterRiskScoreHMLCondition
):
    field: str
    negated: bool
    risk_score_id: Annotated[str, Field(alias="riskScoreId")]
    risk_score_type: Annotated[
        Literal["HML"], Field(alias="riskScoreType", title="Filter Risk Score Type")
    ]
    type: Annotated[Literal["RISK_SCORE"], Field(title="Filter Condition Type")]
    values: Annotated[
        list[ApiFilterRiskScoreHMLConditionValue],
        Field(description="A list of HML options to include in the filter."),
    ]


class ApiFilterRiskScorePercentConditionApiFilterRiskScorePercentCondition1(
    ApiFilterRiskScorePercentConditionApiFilterRiskScorePercentCondition
):
    field: str
    negated: bool
    risk_score_id: Annotated[str, Field(alias="riskScoreId")]
    risk_score_percent_type: Annotated[
        Literal[
            "ApiFilterRiskScorePercentCondition#-datamodel-code-generator-#-union_model-0-#-special-#"
        ],
        Field(
            alias="riskScorePercentType",
            description="Determines the type of risk score percent condition to filter.",
            title="Filter Risk Score Percent Type",
        ),
    ]
    risk_score_type: Annotated[
        Literal["PERCENT"], Field(alias="riskScoreType", title="Filter Risk Score Type")
    ]
    type: Annotated[Literal["RISK_SCORE"], Field(title="Filter Condition Type")]


ApiFilterRiskScorePercentRangeCondition = RootModel[
    "ApiFilterRiskScorePercentRangeConditionApiFilterRiskScorePercentRangeCondition2"
]


ApiFilterRiskScorePercentUnscoredCondition = RootModel[
    "ApiFilterRiskScorePercentUnscoredConditionApiFilterRiskScorePercentUnscoredCondition2"
]


ApiFilterRiskScorePercentValueCondition = RootModel[
    "ApiFilterRiskScorePercentValueConditionApiFilterRiskScorePercentValueCondition2"
]


class ApiFilterRiskScorePercentRangeConditionApiFilterRiskScorePercentRangeCondition2(
    ApiFilterRiskScorePercentRangeConditionApiFilterRiskScorePercentRangeCondition
):
    field: str
    negated: bool
    range_end: Annotated[
        int,
        Field(
            alias="rangeEnd",
            description="The end of the number range between 0 and 10,000.",
        ),
    ]
    range_start: Annotated[
        int,
        Field(
            alias="rangeStart",
            description="The start of the number range between 0 and 10,000.",
        ),
    ]
    risk_score_id: Annotated[str, Field(alias="riskScoreId")]
    risk_score_percent_type: Annotated[
        ApiFilterRiskScorePercentRangeConditionRiskScorePercentType,
        Field(alias="riskScorePercentType", title="Filter Risk Score Percent Type"),
    ]
    risk_score_type: Annotated[
        Literal["PERCENT"], Field(alias="riskScoreType", title="Filter Risk Score Type")
    ]
    type: Annotated[Literal["RISK_SCORE"], Field(title="Filter Condition Type")]


class ApiFilterRiskScorePercentUnscoredConditionApiFilterRiskScorePercentUnscoredCondition2(
    ApiFilterRiskScorePercentUnscoredConditionApiFilterRiskScorePercentUnscoredCondition
):
    field: str
    negated: bool
    risk_score_id: Annotated[str, Field(alias="riskScoreId")]
    risk_score_percent_type: Annotated[
        Literal["UNSCORED"],
        Field(alias="riskScorePercentType", title="Filter Risk Score Percent Type"),
    ]
    risk_score_type: Annotated[
        Literal["PERCENT"], Field(alias="riskScoreType", title="Filter Risk Score Type")
    ]
    type: Annotated[Literal["RISK_SCORE"], Field(title="Filter Condition Type")]


class ApiFilterRiskScorePercentValueConditionApiFilterRiskScorePercentValueCondition2(
    ApiFilterRiskScorePercentValueConditionApiFilterRiskScorePercentValueCondition
):
    field: str
    negated: bool
    risk_score_id: Annotated[str, Field(alias="riskScoreId")]
    risk_score_percent_type: Annotated[
        ApiFilterRiskScorePercentValueConditionRiskScorePercentType,
        Field(alias="riskScorePercentType", title="Filter Risk Score Percent Type"),
    ]
    risk_score_type: Annotated[
        Literal["PERCENT"], Field(alias="riskScoreType", title="Filter Risk Score Type")
    ]
    type: Annotated[Literal["RISK_SCORE"], Field(title="Filter Condition Type")]
    value: Annotated[
        int,
        Field(
            description="A number between 0 and 10,000 used as part of a more than, or less than filter."
        ),
    ]


ApiFilterComplexMonetaryFlowCondition = RootModel[
    "ApiFilterComplexMonetaryFlowConditionApiFilterComplexMonetaryFlowCondition2"
]


ApiFilterSimpleMonetaryFlowCondition = RootModel[
    "ApiFilterSimpleMonetaryFlowConditionApiFilterSimpleMonetaryFlowCondition2"
]


ApiFilterSpecificMonetaryFlowCondition = RootModel[
    "ApiFilterSpecificMonetaryFlowConditionApiFilterSpecificMonetaryFlowCondition2"
]


class ApiFilterComplexMonetaryFlowConditionApiFilterComplexMonetaryFlowCondition2(
    ApiFilterComplexMonetaryFlowConditionApiFilterComplexMonetaryFlowCondition
):
    field: str
    monetary_flow_type: Annotated[
        Literal["COMPLEX_FLOW"],
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ]
    negated: bool
    type: Annotated[Literal["MONETARY_FLOW"], Field(title="Filter Condition Type")]


class ApiFilterSimpleMonetaryFlowConditionApiFilterSimpleMonetaryFlowCondition2(
    ApiFilterSimpleMonetaryFlowConditionApiFilterSimpleMonetaryFlowCondition
):
    field: str
    monetary_flow_type: Annotated[
        Literal["SIMPLE_FLOW"],
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ]
    negated: bool
    type: Annotated[Literal["MONETARY_FLOW"], Field(title="Filter Condition Type")]


class ApiFilterSpecificMonetaryFlowConditionApiFilterSpecificMonetaryFlowCondition2(
    ApiFilterSpecificMonetaryFlowConditionApiFilterSpecificMonetaryFlowCondition
):
    credit_account: Annotated[
        ApiFilterAccountSelection,
        Field(
            alias="creditAccount",
            description="The selected credit account in the monetary flow.",
        ),
    ]
    debit_account: Annotated[
        ApiFilterAccountSelection,
        Field(
            alias="debitAccount",
            description="The selected debit account in the monetary flow.",
        ),
    ]
    field: str
    monetary_flow_type: Annotated[
        Literal["SPECIFIC_FLOW"],
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ]
    negated: bool
    specific_monetary_flow_type: Annotated[
        Literal[
            "ApiFilterSpecificMonetaryFlowCondition#-datamodel-code-generator-#-union_model-1-#-special-#"
        ],
        Field(
            alias="specificMonetaryFlowType",
            description="The type of specific monetary flow.",
            title="Filter Specific Monetary Flow Type",
        ),
    ]
    type: Annotated[Literal["MONETARY_FLOW"], Field(title="Filter Condition Type")]


ApiFilterSpecificMonetaryFlowRangeCondition = RootModel[
    "ApiFilterSpecificMonetaryFlowRangeConditionApiFilterSpecificMonetaryFlowRangeCondition2"
]


ApiFilterSpecificMonetaryFlowValueCondition = RootModel[
    "ApiFilterSpecificMonetaryFlowValueConditionApiFilterSpecificMonetaryFlowValueCondition2"
]


class ApiFilterSpecificMonetaryFlowRangeConditionApiFilterSpecificMonetaryFlowRangeCondition2(
    ApiFilterSpecificMonetaryFlowRangeConditionApiFilterSpecificMonetaryFlowRangeCondition
):
    credit_account: Annotated[ApiFilterAccountSelection, Field(alias="creditAccount")]
    debit_account: Annotated[ApiFilterAccountSelection, Field(alias="debitAccount")]
    field: str
    monetary_flow_type: Annotated[
        Literal["SPECIFIC_FLOW"],
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ]
    negated: bool
    range_end: Annotated[
        int,
        Field(
            alias="rangeEnd",
            description="The end of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ]
    range_start: Annotated[
        int,
        Field(
            alias="rangeStart",
            description="The start of the range, as a MONEY_100 formatted number to compare with entries.",
        ),
    ]
    specific_monetary_flow_type: Annotated[
        Literal["BETWEEN"],
        Field(
            alias="specificMonetaryFlowType", title="Filter Specific Monetary Flow Type"
        ),
    ]
    type: Annotated[Literal["MONETARY_FLOW"], Field(title="Filter Condition Type")]


class ApiFilterSpecificMonetaryFlowValueConditionApiFilterSpecificMonetaryFlowValueCondition2(
    ApiFilterSpecificMonetaryFlowValueConditionApiFilterSpecificMonetaryFlowValueCondition
):
    credit_account: Annotated[ApiFilterAccountSelection, Field(alias="creditAccount")]
    debit_account: Annotated[ApiFilterAccountSelection, Field(alias="debitAccount")]
    field: str
    monetary_flow_type: Annotated[
        Literal["SPECIFIC_FLOW"],
        Field(alias="monetaryFlowType", title="Filter Monetary Flow Type"),
    ]
    negated: bool
    specific_monetary_flow_type: Annotated[
        ApiFilterSpecificMonetaryFlowValueConditionSpecificMonetaryFlowType,
        Field(
            alias="specificMonetaryFlowType", title="Filter Specific Monetary Flow Type"
        ),
    ]
    type: Annotated[Literal["MONETARY_FLOW"], Field(title="Filter Condition Type")]
    value: Annotated[
        int,
        Field(description="The MONEY_100 formatted number to compare with entries."),
    ]


ApiFilterAccountCondition = RootModel[
    Union[
        "ApiFilterAccountConditionApiFilterAccountCondition14",
        "ApiFilterAccountConditionApiFilterAccountCondition15",
        "ApiFilterAccountConditionApiFilterAccountCondition16",
        "ApiFilterAccountConditionApiFilterAccountCondition17",
        "ApiFilterAccountConditionApiFilterAccountCondition18",
        "ApiFilterAccountConditionApiFilterAccountCondition19",
        "ApiFilterAccountConditionApiFilterAccountCondition20",
        "ApiFilterAccountConditionApiFilterAccountCondition21",
        "ApiFilterAccountConditionApiFilterAccountCondition22",
        "ApiFilterAccountConditionApiFilterAccountCondition23",
        "ApiFilterAccountConditionApiFilterAccountCondition24",
        "ApiFilterAccountConditionApiFilterAccountCondition25",
        "ApiFilterAccountConditionApiFilterAccountCondition26",
    ]
]


ApiFilterControlPointCondition = RootModel[
    Union[
        "ApiFilterControlPointConditionApiFilterControlPointCondition14",
        "ApiFilterControlPointConditionApiFilterControlPointCondition15",
        "ApiFilterControlPointConditionApiFilterControlPointCondition16",
        "ApiFilterControlPointConditionApiFilterControlPointCondition17",
        "ApiFilterControlPointConditionApiFilterControlPointCondition18",
        "ApiFilterControlPointConditionApiFilterControlPointCondition19",
        "ApiFilterControlPointConditionApiFilterControlPointCondition20",
        "ApiFilterControlPointConditionApiFilterControlPointCondition21",
        "ApiFilterControlPointConditionApiFilterControlPointCondition22",
        "ApiFilterControlPointConditionApiFilterControlPointCondition23",
        "ApiFilterControlPointConditionApiFilterControlPointCondition24",
        "ApiFilterControlPointConditionApiFilterControlPointCondition25",
        "ApiFilterControlPointConditionApiFilterControlPointCondition26",
    ]
]


ApiFilterDateCondition = RootModel[
    Union[
        "ApiFilterDateConditionApiFilterDateCondition14",
        "ApiFilterDateConditionApiFilterDateCondition15",
        "ApiFilterDateConditionApiFilterDateCondition16",
        "ApiFilterDateConditionApiFilterDateCondition17",
        "ApiFilterDateConditionApiFilterDateCondition18",
        "ApiFilterDateConditionApiFilterDateCondition19",
        "ApiFilterDateConditionApiFilterDateCondition20",
        "ApiFilterDateConditionApiFilterDateCondition21",
        "ApiFilterDateConditionApiFilterDateCondition22",
        "ApiFilterDateConditionApiFilterDateCondition23",
        "ApiFilterDateConditionApiFilterDateCondition24",
        "ApiFilterDateConditionApiFilterDateCondition25",
        "ApiFilterDateConditionApiFilterDateCondition26",
    ]
]


ApiFilterGroupCondition = RootModel[
    Union[
        "ApiFilterGroupConditionApiFilterGroupCondition14",
        "ApiFilterGroupConditionApiFilterGroupCondition15",
        "ApiFilterGroupConditionApiFilterGroupCondition16",
        "ApiFilterGroupConditionApiFilterGroupCondition17",
        "ApiFilterGroupConditionApiFilterGroupCondition18",
        "ApiFilterGroupConditionApiFilterGroupCondition19",
        "ApiFilterGroupConditionApiFilterGroupCondition20",
        "ApiFilterGroupConditionApiFilterGroupCondition21",
        "ApiFilterGroupConditionApiFilterGroupCondition22",
        "ApiFilterGroupConditionApiFilterGroupCondition23",
        "ApiFilterGroupConditionApiFilterGroupCondition24",
        "ApiFilterGroupConditionApiFilterGroupCondition25",
        "ApiFilterGroupConditionApiFilterGroupCondition26",
    ]
]


ApiFilterGroupConditionUpdate = RootModel[
    Union[
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate14",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate15",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate16",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate17",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate18",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate19",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate20",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate21",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate22",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate23",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate24",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate25",
        "ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate26",
    ]
]


ApiFilterMaterialityCondition = RootModel[
    Union[
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition14",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition15",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition16",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition17",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition18",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition19",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition20",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition21",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition22",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition23",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition24",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition25",
        "ApiFilterMaterialityConditionApiFilterMaterialityCondition26",
    ]
]


ApiFilterMonetaryFlowCondition = RootModel[
    Union[
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition14",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition15",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition16",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition17",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition18",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition19",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition20",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition21",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition22",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition23",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition24",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition25",
        "ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition26",
    ]
]


ApiFilterMonetaryValueCondition = RootModel[
    Union[
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition14",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition15",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition16",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition17",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition18",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition19",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition20",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition21",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition22",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition23",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition24",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition25",
        "ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition26",
    ]
]


ApiFilterNumericalValueCondition = RootModel[
    Union[
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition14",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition15",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition16",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition17",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition18",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition19",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition20",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition21",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition22",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition23",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition24",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition25",
        "ApiFilterNumericalValueConditionApiFilterNumericalValueCondition26",
    ]
]


ApiFilterPopulationsCondition = RootModel[
    Union[
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition14",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition15",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition16",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition17",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition18",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition19",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition20",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition21",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition22",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition23",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition24",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition25",
        "ApiFilterPopulationsConditionApiFilterPopulationsCondition26",
    ]
]


ApiFilterRiskScoreCondition = RootModel[
    Union[
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition14",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition15",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition16",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition17",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition18",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition19",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition20",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition21",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition22",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition23",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition24",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition25",
        "ApiFilterRiskScoreConditionApiFilterRiskScoreCondition26",
    ]
]


ApiFilterStringArrayCondition = RootModel[
    Union[
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition14",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition15",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition16",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition17",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition18",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition19",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition20",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition21",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition22",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition23",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition24",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition25",
        "ApiFilterStringArrayConditionApiFilterStringArrayCondition26",
    ]
]


ApiFilterStringCondition = RootModel[
    Union[
        "ApiFilterStringConditionApiFilterStringCondition14",
        "ApiFilterStringConditionApiFilterStringCondition15",
        "ApiFilterStringConditionApiFilterStringCondition16",
        "ApiFilterStringConditionApiFilterStringCondition17",
        "ApiFilterStringConditionApiFilterStringCondition18",
        "ApiFilterStringConditionApiFilterStringCondition19",
        "ApiFilterStringConditionApiFilterStringCondition20",
        "ApiFilterStringConditionApiFilterStringCondition21",
        "ApiFilterStringConditionApiFilterStringCondition22",
        "ApiFilterStringConditionApiFilterStringCondition23",
        "ApiFilterStringConditionApiFilterStringCondition24",
        "ApiFilterStringConditionApiFilterStringCondition25",
        "ApiFilterStringConditionApiFilterStringCondition26",
    ]
]


ApiFilterTypeaheadEntryCondition = RootModel[
    Union[
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition14",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition15",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition16",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition17",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition18",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition19",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition20",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition21",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition22",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition23",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition24",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition25",
        "ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition26",
    ]
]


ApiFilterGroupConditionRead = RootModel[
    Union[
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead14",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead15",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead16",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead17",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead18",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead19",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead20",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead21",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead22",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead23",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead24",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead25",
        "ApiFilterGroupConditionReadApiFilterGroupConditionRead26",
    ]
]


ApiFilterGroupConditionCreate = RootModel[
    Union[
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate14",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate15",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate16",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate17",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate18",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate19",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate20",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate21",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate22",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate23",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate24",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate25",
        "ApiFilterGroupConditionCreateApiFilterGroupConditionCreate26",
    ]
]


class ApiFilterAccountConditionApiFilterAccountCondition4(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition4(BaseItem):
    type: Annotated[
        Literal["4"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate4(BaseItem):
    type: Annotated[
        Literal["4"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition4(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition4(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition4(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate4(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition4(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition4(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition4(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition4(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition4(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition4(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition4(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition4(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition4(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead4(BaseItem):
    type: Annotated[
        Literal["4"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead4(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate4(BaseItem):
    type: Annotated[
        Literal["4"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate4(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition3(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition3(BaseItem):
    type: Annotated[
        Literal["3"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate3(BaseItem):
    type: Annotated[
        Literal["3"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition3(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition3(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition3(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate3(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition3(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition3(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition3(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition3(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition3(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition3(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition3(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition3(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition3(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead3(BaseItem):
    type: Annotated[
        Literal["3"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead3(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate3(BaseItem):
    type: Annotated[
        Literal["3"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate3(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition12(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition12(BaseItem):
    type: Annotated[
        Literal["12"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate12(BaseItem):
    type: Annotated[
        Literal["12"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition12(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition12(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition12(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate12(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition12(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition12(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition12(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition12(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition12(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition12(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition12(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition12(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition12(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead12(BaseItem):
    type: Annotated[
        Literal["12"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead12(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate12(BaseItem):
    type: Annotated[
        Literal["12"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate12(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition(BaseItem):
    type: Annotated[
        Literal["0"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate(BaseItem):
    type: Annotated[
        Literal["0"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead(BaseItem):
    type: Annotated[
        Literal["0"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate(BaseItem):
    type: Annotated[
        Literal["0"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition10(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition10(BaseItem):
    type: Annotated[
        Literal["10"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate10(BaseItem):
    type: Annotated[
        Literal["10"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition10(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition10(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition10(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate10(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition10(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition10(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition10(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition10(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition10(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition10(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition10(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition10(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition10(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead10(BaseItem):
    type: Annotated[
        Literal["10"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead10(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate10(BaseItem):
    type: Annotated[
        Literal["10"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate10(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition8(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition8(BaseItem):
    type: Annotated[
        Literal["8"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate8(BaseItem):
    type: Annotated[
        Literal["8"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition8(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition8(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition8(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate8(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition8(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition8(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition8(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition8(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition8(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition8(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition8(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition8(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition8(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead8(BaseItem):
    type: Annotated[
        Literal["8"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead8(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate8(BaseItem):
    type: Annotated[
        Literal["8"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate8(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition9(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition9(BaseItem):
    type: Annotated[
        Literal["9"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate9(BaseItem):
    type: Annotated[
        Literal["9"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition9(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition9(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition9(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate9(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition9(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition9(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition9(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition9(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition9(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition9(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition9(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition9(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition9(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead9(BaseItem):
    type: Annotated[
        Literal["9"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead9(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate9(BaseItem):
    type: Annotated[
        Literal["9"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate9(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition11(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition11(BaseItem):
    type: Annotated[
        Literal["11"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate11(BaseItem):
    type: Annotated[
        Literal["11"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition11(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition11(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition11(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate11(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition11(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition11(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition11(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition11(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition11(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition11(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition11(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition11(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition11(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead11(BaseItem):
    type: Annotated[
        Literal["11"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead11(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate11(BaseItem):
    type: Annotated[
        Literal["11"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate11(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition6(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition6(BaseItem):
    type: Annotated[
        Literal["6"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate6(BaseItem):
    type: Annotated[
        Literal["6"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition6(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition6(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition6(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate6(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition6(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition6(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition6(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition6(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition6(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition6(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition6(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition6(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition6(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead6(BaseItem):
    type: Annotated[
        Literal["6"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead6(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate6(BaseItem):
    type: Annotated[
        Literal["6"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate6(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition7(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition7(BaseItem):
    type: Annotated[
        Literal["7"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate7(BaseItem):
    type: Annotated[
        Literal["7"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition7(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition7(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition7(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate7(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition7(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition7(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition7(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition7(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition7(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition7(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition7(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition7(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition7(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead7(BaseItem):
    type: Annotated[
        Literal["7"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead7(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate7(BaseItem):
    type: Annotated[
        Literal["7"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate7(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition2(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition2(BaseItem):
    type: Annotated[
        Literal["2"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate2(BaseItem):
    type: Annotated[
        Literal["2"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition2(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition2(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition2(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate2(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition2(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition2(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition2(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition2(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition2(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition2(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition2(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition2(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition2(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead2(BaseItem):
    type: Annotated[
        Literal["2"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead2(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate2(BaseItem):
    type: Annotated[
        Literal["2"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate2(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition1(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition1(BaseItem):
    type: Annotated[
        Literal["1"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate1(BaseItem):
    type: Annotated[
        Literal["1"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition1(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition1(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition1(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate1(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition1(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition1(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition1(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition1(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition1(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition1(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition1(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition1(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition1(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead1(BaseItem):
    type: Annotated[
        Literal["1"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead1(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate1(BaseItem):
    type: Annotated[
        Literal["1"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate1(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition5(BaseItem):
    type: Annotated[
        ApiFilterAccountConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionApiFilterCondition5(BaseItem):
    type: Annotated[
        Literal["5"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterConditionUpdateApiFilterConditionUpdate5(BaseItem):
    type: Annotated[
        Literal["5"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition5(BaseItem):
    type: Annotated[
        ApiFilterControlPointConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterDateConditionApiFilterDateCondition5(BaseItem):
    type: Annotated[
        ApiFilterDateConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionApiFilterGroupCondition5(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate5(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionUpdateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMaterialityConditionApiFilterMaterialityCondition5(BaseItem):
    type: Annotated[
        ApiFilterMaterialityConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition5(BaseItem):
    type: Annotated[
        ApiFilterMonetaryFlowConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition5(BaseItem):
    type: Annotated[
        ApiFilterMonetaryValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition5(BaseItem):
    type: Annotated[
        ApiFilterNumericalValueConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterPopulationsConditionApiFilterPopulationsCondition5(BaseItem):
    type: Annotated[
        ApiFilterPopulationsConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition5(BaseItem):
    type: Annotated[
        ApiFilterRiskScoreConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringArrayConditionApiFilterStringArrayCondition5(BaseItem):
    type: Annotated[
        ApiFilterStringArrayConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterStringConditionApiFilterStringCondition5(BaseItem):
    type: Annotated[
        ApiFilterStringConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition5(BaseItem):
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionReadApiFilterConditionRead5(BaseItem):
    type: Annotated[
        Literal["5"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead5(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionReadType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterConditionCreateApiFilterConditionCreate5(BaseItem):
    type: Annotated[
        Literal["5"],
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate5(BaseItem):
    type: Annotated[
        ApiFilterGroupConditionCreateType | None,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ] = None


class ApiFilterAccountConditionApiFilterAccountCondition18(
    ApiFilterAccountConditionApiFilterAccountCondition4,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition18(
    ApiFilterControlPointConditionApiFilterControlPointCondition4,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition18(
    ApiFilterDateConditionApiFilterDateCondition4,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-4-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition18(
    ApiFilterGroupConditionApiFilterGroupCondition4,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate18(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate4,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition18(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition4,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-4-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition18(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition4,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-4-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition18(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition4,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-4-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition18(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition4,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-4-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition18(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition4,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition18(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition4,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-4-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition18(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition4,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition18(
    ApiFilterStringConditionApiFilterStringCondition4,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition18(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition4,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead18(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead4,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate18(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate4,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition17(
    ApiFilterAccountConditionApiFilterAccountCondition3,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition17(
    ApiFilterControlPointConditionApiFilterControlPointCondition3,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition17(
    ApiFilterDateConditionApiFilterDateCondition3,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-3-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition17(
    ApiFilterGroupConditionApiFilterGroupCondition3,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate17(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate3,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition17(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition3,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-3-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition17(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition3,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-3-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition17(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition3,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-3-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition17(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition3,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-3-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition17(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition3,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition17(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition3,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-3-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition17(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition3,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition17(
    ApiFilterStringConditionApiFilterStringCondition3,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition17(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition3,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead17(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead3,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate17(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate3,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition26(
    ApiFilterAccountConditionApiFilterAccountCondition12,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition26(
    ApiFilterControlPointConditionApiFilterControlPointCondition12,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition26(
    ApiFilterDateConditionApiFilterDateCondition12,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-12-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition26(
    ApiFilterGroupConditionApiFilterGroupCondition12,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate26(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate12,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition26(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition12,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-12-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition26(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition12,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-12-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition26(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition12,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-12-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition26(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition12,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-12-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition26(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition12,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition26(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition12,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-12-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition26(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition12,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition26(
    ApiFilterStringConditionApiFilterStringCondition12,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition26(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition12,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead26(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead12,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate26(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate12,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition14(
    ApiFilterAccountConditionApiFilterAccountCondition,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition14(
    ApiFilterControlPointConditionApiFilterControlPointCondition,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition14(
    ApiFilterDateConditionApiFilterDateCondition,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-0-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition14(
    ApiFilterGroupConditionApiFilterGroupCondition,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate14(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition14(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-0-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition14(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-0-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition14(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-0-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition14(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-0-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition14(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition14(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-0-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition14(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition14(
    ApiFilterStringConditionApiFilterStringCondition,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition14(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead14(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate14(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition24(
    ApiFilterAccountConditionApiFilterAccountCondition10,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition24(
    ApiFilterControlPointConditionApiFilterControlPointCondition10,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition24(
    ApiFilterDateConditionApiFilterDateCondition10,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-10-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition24(
    ApiFilterGroupConditionApiFilterGroupCondition10,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate24(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate10,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition24(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition10,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-10-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition24(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition10,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-10-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition24(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition10,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-10-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition24(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition10,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-10-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition24(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition10,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition24(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition10,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-10-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition24(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition10,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition24(
    ApiFilterStringConditionApiFilterStringCondition10,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition24(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition10,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead24(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead10,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate24(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate10,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition22(
    ApiFilterAccountConditionApiFilterAccountCondition8,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition22(
    ApiFilterControlPointConditionApiFilterControlPointCondition8,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition22(
    ApiFilterDateConditionApiFilterDateCondition8,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-8-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition22(
    ApiFilterGroupConditionApiFilterGroupCondition8,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate22(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate8,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition22(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition8,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-8-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition22(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition8,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-8-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition22(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition8,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-8-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition22(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition8,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-8-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition22(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition8,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition22(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition8,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-8-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition22(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition8,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition22(
    ApiFilterStringConditionApiFilterStringCondition8,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition22(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition8,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead22(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead8,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate22(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate8,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition23(
    ApiFilterAccountConditionApiFilterAccountCondition9,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition23(
    ApiFilterControlPointConditionApiFilterControlPointCondition9,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition23(
    ApiFilterDateConditionApiFilterDateCondition9,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-9-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition23(
    ApiFilterGroupConditionApiFilterGroupCondition9,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate23(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate9,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition23(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition9,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-9-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition23(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition9,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-9-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition23(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition9,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-9-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition23(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition9,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-9-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition23(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition9,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition23(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition9,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-9-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition23(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition9,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition23(
    ApiFilterStringConditionApiFilterStringCondition9,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition23(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition9,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead23(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead9,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate23(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate9,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition25(
    ApiFilterAccountConditionApiFilterAccountCondition11,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition25(
    ApiFilterControlPointConditionApiFilterControlPointCondition11,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition25(
    ApiFilterDateConditionApiFilterDateCondition11,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-11-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition25(
    ApiFilterGroupConditionApiFilterGroupCondition11,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate25(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate11,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition25(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition11,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-11-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition25(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition11,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-11-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition25(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition11,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-11-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition25(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition11,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-11-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition25(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition11,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition25(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition11,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-11-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition25(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition11,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition25(
    ApiFilterStringConditionApiFilterStringCondition11,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition25(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition11,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead25(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead11,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate25(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate11,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition20(
    ApiFilterAccountConditionApiFilterAccountCondition6,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition20(
    ApiFilterControlPointConditionApiFilterControlPointCondition6,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition20(
    ApiFilterDateConditionApiFilterDateCondition6,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-6-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition20(
    ApiFilterGroupConditionApiFilterGroupCondition6,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate20(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate6,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition20(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition6,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-6-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition20(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition6,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-6-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition20(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition6,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-6-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition20(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition6,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-6-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition20(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition6,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition20(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition6,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-6-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition20(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition6,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition20(
    ApiFilterStringConditionApiFilterStringCondition6,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition20(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition6,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead20(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead6,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate20(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate6,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition21(
    ApiFilterAccountConditionApiFilterAccountCondition7,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition21(
    ApiFilterControlPointConditionApiFilterControlPointCondition7,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition21(
    ApiFilterDateConditionApiFilterDateCondition7,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-7-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition21(
    ApiFilterGroupConditionApiFilterGroupCondition7,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate21(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate7,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition21(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition7,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-7-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition21(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition7,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-7-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition21(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition7,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-7-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition21(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition7,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-7-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition21(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition7,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition21(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition7,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-7-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition21(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition7,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition21(
    ApiFilterStringConditionApiFilterStringCondition7,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition21(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition7,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead21(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead7,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate21(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate7,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition16(
    ApiFilterAccountConditionApiFilterAccountCondition2,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition16(
    ApiFilterControlPointConditionApiFilterControlPointCondition2,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition16(
    ApiFilterDateConditionApiFilterDateCondition2,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-2-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition16(
    ApiFilterGroupConditionApiFilterGroupCondition2,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate16(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate2,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition16(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition2,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-2-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition16(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition2,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-2-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition16(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition2,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-2-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition16(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition2,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-2-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition16(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition2,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition16(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition2,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-2-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition16(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition2,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition16(
    ApiFilterStringConditionApiFilterStringCondition2,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition16(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition2,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead16(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead2,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate16(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate2,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition15(
    ApiFilterAccountConditionApiFilterAccountCondition1,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterControlPointConditionApiFilterControlPointCondition15(
    ApiFilterControlPointConditionApiFilterControlPointCondition1,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition15(
    ApiFilterDateConditionApiFilterDateCondition1,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-1-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition15(
    ApiFilterGroupConditionApiFilterGroupCondition1,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate15(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate1,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition15(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition1,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-1-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition15(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition1,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-1-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition15(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition1,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-1-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition15(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition1,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-1-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition15(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition1,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition15(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition1,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-1-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition15(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition1,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition15(
    ApiFilterStringConditionApiFilterStringCondition1,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition15(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition1,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead15(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead1,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate15(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate1,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterAccountConditionApiFilterAccountCondition19(
    ApiFilterAccountConditionApiFilterAccountCondition5,
    ApiFilterAccountConditionApiFilterAccountCondition13,
):
    account_selections: Annotated[
        list[ApiFilterAccountSelection], Field(alias="accountSelections")
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterAccountConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


ApiFilterCondition = RootModel[
    ApiFilterConditionApiFilterCondition
    | ApiFilterConditionApiFilterCondition1
    | ApiFilterConditionApiFilterCondition2
    | ApiFilterConditionApiFilterCondition3
    | ApiFilterConditionApiFilterCondition4
    | ApiFilterConditionApiFilterCondition5
    | ApiFilterConditionApiFilterCondition6
    | ApiFilterConditionApiFilterCondition7
    | ApiFilterConditionApiFilterCondition8
    | ApiFilterConditionApiFilterCondition9
    | ApiFilterConditionApiFilterCondition10
    | ApiFilterConditionApiFilterCondition11
    | ApiFilterConditionApiFilterCondition12
    | None
]


ApiFilterConditionUpdate = RootModel[
    ApiFilterConditionUpdateApiFilterConditionUpdate
    | ApiFilterConditionUpdateApiFilterConditionUpdate1
    | ApiFilterConditionUpdateApiFilterConditionUpdate2
    | ApiFilterConditionUpdateApiFilterConditionUpdate3
    | ApiFilterConditionUpdateApiFilterConditionUpdate4
    | ApiFilterConditionUpdateApiFilterConditionUpdate5
    | ApiFilterConditionUpdateApiFilterConditionUpdate6
    | ApiFilterConditionUpdateApiFilterConditionUpdate7
    | ApiFilterConditionUpdateApiFilterConditionUpdate8
    | ApiFilterConditionUpdateApiFilterConditionUpdate9
    | ApiFilterConditionUpdateApiFilterConditionUpdate10
    | ApiFilterConditionUpdateApiFilterConditionUpdate11
    | ApiFilterConditionUpdateApiFilterConditionUpdate12
    | None
]


class ApiFilterControlPointConditionApiFilterControlPointCondition19(
    ApiFilterControlPointConditionApiFilterControlPointCondition5,
    ApiFilterControlPointConditionApiFilterControlPointCondition13,
):
    control_points: Annotated[
        list[ApiFilterControlPointSelection],
        Field(alias="controlPoints", description="A list of control point selections."),
    ]
    field: str
    negated: bool
    risk_level: Annotated[
        ApiFilterControlPointConditionRiskLevel,
        Field(
            alias="riskLevel",
            description="The risk level of the selected control points.",
            title="Filter Control Point Risk Level",
        ),
    ]
    type: Annotated[
        ApiFilterControlPointConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterDateConditionApiFilterDateCondition19(
    ApiFilterDateConditionApiFilterDateCondition5,
    ApiFilterDateConditionApiFilterDateCondition13,
):
    date_type: Annotated[
        Literal[
            "ApiFilterDateCondition#-datamodel-code-generator-#-union_model-5-#-special-#"
        ],
        Field(
            alias="dateType",
            description="The type of date condition.",
            title="Filter Date Type",
        ),
    ]
    field: str
    negated: bool
    type: Annotated[
        ApiFilterDateConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionApiFilterGroupCondition19(
    ApiFilterGroupConditionApiFilterGroupCondition5,
    ApiFilterGroupConditionApiFilterGroupCondition13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate19(
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate5,
    ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionUpdateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionUpdateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMaterialityConditionApiFilterMaterialityCondition19(
    ApiFilterMaterialityConditionApiFilterMaterialityCondition5,
    ApiFilterMaterialityConditionApiFilterMaterialityCondition13,
):
    field: str
    materiality_option: Annotated[
        Literal[
            "ApiFilterMaterialityCondition#-datamodel-code-generator-#-union_model-5-#-special-#"
        ],
        Field(
            alias="materialityOption",
            description="The type of materiality comparison.",
            title="Filter Materiality Value Options",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMaterialityConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition19(
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition5,
    ApiFilterMonetaryFlowConditionApiFilterMonetaryFlowCondition13,
):
    field: str
    monetary_flow_type: Annotated[
        Literal[
            "ApiFilterMonetaryFlowCondition#-datamodel-code-generator-#-union_model-5-#-special-#"
        ],
        Field(
            alias="monetaryFlowType",
            description="The type of monetary flow this filter will match.",
            title="Filter Monetary Flow Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryFlowConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition19(
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition5,
    ApiFilterMonetaryValueConditionApiFilterMonetaryValueCondition13,
):
    field: str
    monetary_value_type: Annotated[
        Literal[
            "ApiFilterMonetaryValueCondition#-datamodel-code-generator-#-union_model-5-#-special-#"
        ],
        Field(
            alias="monetaryValueType",
            description="The type of monetary value condition.",
            title="Filter Monetary Type",
        ),
    ]
    negated: bool
    type: Annotated[
        ApiFilterMonetaryValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterNumericalValueConditionApiFilterNumericalValueCondition19(
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition5,
    ApiFilterNumericalValueConditionApiFilterNumericalValueCondition13,
):
    field: str
    negated: bool
    numerical_value_type: Annotated[
        Literal[
            "ApiFilterNumericalValueCondition#-datamodel-code-generator-#-union_model-5-#-special-#"
        ],
        Field(
            alias="numericalValueType",
            description="The type of numerical value condition.",
            title="Filter Numerical Value Type",
        ),
    ]
    type: Annotated[
        ApiFilterNumericalValueConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterPopulationsConditionApiFilterPopulationsCondition19(
    ApiFilterPopulationsConditionApiFilterPopulationsCondition5,
    ApiFilterPopulationsConditionApiFilterPopulationsCondition13,
):
    field: str
    negated: bool
    population_ids: Annotated[
        list[str],
        Field(
            alias="populationIds",
            description="A list of population IDs and category names to be used in the filter.",
        ),
    ]
    type: Annotated[
        ApiFilterPopulationsConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterRiskScoreConditionApiFilterRiskScoreCondition19(
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition5,
    ApiFilterRiskScoreConditionApiFilterRiskScoreCondition13,
):
    field: str
    negated: bool
    risk_score_id: Annotated[
        str,
        Field(alias="riskScoreId", description="The risk score column being filtered."),
    ]
    risk_score_type: Annotated[
        Literal[
            "ApiFilterRiskScoreCondition#-datamodel-code-generator-#-union_model-5-#-special-#"
        ],
        Field(
            alias="riskScoreType",
            description="Determines if the filter will test entries using high, medium or low scores, or if it will match by percentage.",
            title="Filter Risk Score Type",
        ),
    ]
    type: Annotated[
        ApiFilterRiskScoreConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


class ApiFilterStringArrayConditionApiFilterStringArrayCondition19(
    ApiFilterStringArrayConditionApiFilterStringArrayCondition5,
    ApiFilterStringArrayConditionApiFilterStringArrayCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringArrayConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[str], Field(description="The set of text values used to filter entries.")
    ]


class ApiFilterStringConditionApiFilterStringCondition19(
    ApiFilterStringConditionApiFilterStringCondition5,
    ApiFilterStringConditionApiFilterStringCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterStringConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    value: Annotated[str, Field(description="The text value used to filter entries.")]


class ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition19(
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition5,
    ApiFilterTypeaheadEntryConditionApiFilterTypeaheadEntryCondition13,
):
    field: str
    negated: bool
    type: Annotated[
        ApiFilterTypeaheadEntryConditionType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]
    values: Annotated[
        list[ApiTypeaheadEntry],
        Field(
            description="A list of typeahead entry selections to be used in the filter."
        ),
    ]


ApiFilterConditionRead = RootModel[
    ApiFilterConditionReadApiFilterConditionRead
    | ApiFilterConditionReadApiFilterConditionRead1
    | ApiFilterConditionReadApiFilterConditionRead2
    | ApiFilterConditionReadApiFilterConditionRead3
    | ApiFilterConditionReadApiFilterConditionRead4
    | ApiFilterConditionReadApiFilterConditionRead5
    | ApiFilterConditionReadApiFilterConditionRead6
    | ApiFilterConditionReadApiFilterConditionRead7
    | ApiFilterConditionReadApiFilterConditionRead8
    | ApiFilterConditionReadApiFilterConditionRead9
    | ApiFilterConditionReadApiFilterConditionRead10
    | ApiFilterConditionReadApiFilterConditionRead11
    | ApiFilterConditionReadApiFilterConditionRead12
    | None
]


class ApiFilterGroupConditionReadApiFilterGroupConditionRead19(
    ApiFilterGroupConditionReadApiFilterGroupConditionRead5,
    ApiFilterGroupConditionReadApiFilterGroupConditionRead13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionReadOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionReadType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


ApiFilterConditionCreate = RootModel[
    ApiFilterConditionCreateApiFilterConditionCreate
    | ApiFilterConditionCreateApiFilterConditionCreate1
    | ApiFilterConditionCreateApiFilterConditionCreate2
    | ApiFilterConditionCreateApiFilterConditionCreate3
    | ApiFilterConditionCreateApiFilterConditionCreate4
    | ApiFilterConditionCreateApiFilterConditionCreate5
    | ApiFilterConditionCreateApiFilterConditionCreate6
    | ApiFilterConditionCreateApiFilterConditionCreate7
    | ApiFilterConditionCreateApiFilterConditionCreate8
    | ApiFilterConditionCreateApiFilterConditionCreate9
    | ApiFilterConditionCreateApiFilterConditionCreate10
    | ApiFilterConditionCreateApiFilterConditionCreate11
    | ApiFilterConditionCreateApiFilterConditionCreate12
    | None
]


class ApiFilterGroupConditionCreateApiFilterGroupConditionCreate19(
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate5,
    ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13,
):
    conditions: Annotated[
        list[ApiFilterCondition],
        Field(description="The entries within this condition group.", min_length=1),
    ]
    operator: Annotated[
        ApiFilterGroupConditionCreateOperator,
        Field(
            description="The operator to be applied to conditions within this group.",
            title="Filter Group Operator",
        ),
    ]
    type: Annotated[
        ApiFilterGroupConditionCreateType,
        Field(description="The type of condition.", title="Filter Condition Type"),
    ]


ApiFilterGroupConditionApiFilterGroupCondition13.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate13.model_rebuild()
ApiFilterUpdate.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead13.model_rebuild()
ApiFilterRead.model_rebuild()
ApiPopulationTagUpdate.model_rebuild()
ApiPopulationTagRead.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate13.model_rebuild()
ApiFilterCreate.model_rebuild()
ApiPopulationTagCreate.model_rebuild()
ApiDataTableExportToFileManagerRequestCreate.model_rebuild()
ApiDataTableExportRequest.model_rebuild()
ApiDataTableQueryRead.model_rebuild()
MindBridgeQueryTermMindBridgeQueryTerm14.model_rebuild()
MindBridgeQueryTermMindBridgeQueryTerm15.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition18.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate18.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead18.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate18.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition17.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate17.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead17.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate17.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition26.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate26.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead26.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate26.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition14.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate14.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead14.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate14.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition24.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate24.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead24.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate24.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition22.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate22.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead22.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate22.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition23.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate23.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead23.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate23.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition25.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate25.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead25.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate25.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition20.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate20.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead20.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate20.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition21.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate21.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead21.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate21.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition16.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate16.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead16.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate16.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition15.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate15.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead15.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate15.model_rebuild()
ApiFilterGroupConditionApiFilterGroupCondition19.model_rebuild()
ApiFilterGroupConditionUpdateApiFilterGroupConditionUpdate19.model_rebuild()
ApiFilterGroupConditionReadApiFilterGroupConditionRead19.model_rebuild()
ApiFilterGroupConditionCreateApiFilterGroupConditionCreate19.model_rebuild()
