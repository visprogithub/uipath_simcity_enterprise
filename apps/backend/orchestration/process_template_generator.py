"""
ProcessTemplateGenerator: generates importable UiPath Studio process templates
(XAML skeleton + project.json) for each of the 5 Maestro City automation processes.
"""
import json
import time
from typing import Any, Dict, List, Optional


# ─── XAML Templates ───────────────────────────────────────────────────────────

_XAML_INCIDENT_ESCALATION = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sap2020"
    x:Class="MaestroCity.Incident_Escalation"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"
    xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
    xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
    xmlns:sap2020="http://schemas.microsoft.com/netfx/2020/xaml/activities/presentation"
    xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <!-- Input Arguments -->
    <x:Property Name="in_BuildingId" Type="InArgument(x:String)" />
    <x:Property Name="in_BuildingName" Type="InArgument(x:String)" />
    <x:Property Name="in_Severity" Type="InArgument(x:String)" />
    <x:Property Name="in_OperationalStability" Type="InArgument(x:Double)" />
    <x:Property Name="in_AffectedWorkflows" Type="InArgument(x:Int32)" />
    <!-- Output Arguments -->
    <x:Property Name="out_EscalationId" Type="OutArgument(x:String)" />
    <x:Property Name="out_EscalationLevel" Type="OutArgument(x:Int32)" />
    <x:Property Name="out_NotificationsSent" Type="OutArgument(x:Int32)" />
    <x:Property Name="out_ActionsTaken" Type="OutArgument(scg:List(x:String))" />
    <x:Property Name="out_EstimatedResolutionMinutes" Type="OutArgument(x:Int32)" />
  </x:Members>
  <mva:VisualBasic.Settings>
    <mva:VisualBasicSettings>
      <mva:VisualBasicSettings.ImportedNamespaces>
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System" />
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System.Collections.Generic" />
      </mva:VisualBasicSettings.ImportedNamespaces>
    </mva:VisualBasicSettings>
  </mva:VisualBasic.Settings>
  <Sequence DisplayName="Incident Escalation — Main">
    <Sequence.Variables>
      <Variable Name="v_EscalationId" Type="x:String" />
      <Variable Name="v_EscalationLevel" Type="x:Int32" Default="1" />
      <Variable Name="v_ActionList" Type="scg:List(x:String)" Default="[New List(Of String)]" />
      <Variable Name="v_NotificationCount" Type="x:Int32" Default="0" />
    </Sequence.Variables>

    <!-- Step 1: Log incident receipt -->
    <WriteLine Text="[Incident_Escalation] Received incident for building: {in_BuildingId.Get(context)} severity={in_Severity.Get(context)}" />

    <!-- Step 2: Generate escalation ID -->
    <Assign>
      <Assign.To>
        <OutArgument x:TypeArguments="x:String">[v_EscalationId]</OutArgument>
      </Assign.To>
      <Assign.Value>
        <InArgument x:TypeArguments="x:String">["ESC-" + DateTime.Now.ToString("yyyyMMddHHmmss") + "-" + in_BuildingId.Get(context).ToUpper()]</InArgument>
      </Assign.Value>
    </Assign>

    <!-- Step 3: Determine escalation level based on severity and stability -->
    <If Condition="[in_Severity.Get(context) = &quot;critical&quot; OrElse in_OperationalStability.Get(context) &lt; 30]">
      <If.Then>
        <Sequence DisplayName="Critical Escalation — Level 3">
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_EscalationLevel]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Int32">[3]</InArgument></Assign.Value>
          </Assign>
          <WriteLine Text="[Incident_Escalation] CRITICAL: Escalating to Level 3 — executive notification required" />
          <!-- TODO: Add UiPath Action Center task creation for executive approval -->
          <!-- TODO: Add PagerDuty API call for on-call engineer notification -->
          <!-- TODO: Add ServiceNow major incident record creation -->
        </Sequence>
      </If.Then>
      <If.Else>
        <If Condition="[in_Severity.Get(context) = &quot;warning&quot; OrElse in_OperationalStability.Get(context) &lt; 60]">
          <If.Then>
            <Sequence DisplayName="Warning Escalation — Level 2">
              <Assign>
                <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_EscalationLevel]</OutArgument></Assign.To>
                <Assign.Value><InArgument x:TypeArguments="x:Int32">[2]</InArgument></Assign.Value>
              </Assign>
              <WriteLine Text="[Incident_Escalation] WARNING: Escalating to Level 2 — operations team notified" />
              <!-- TODO: Add Slack webhook notification to #incidents channel -->
              <!-- TODO: Add JIRA ticket creation with P2 priority -->
            </Sequence>
          </If.Then>
          <If.Else>
            <Sequence DisplayName="Info Escalation — Level 1">
              <Assign>
                <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_EscalationLevel]</OutArgument></Assign.To>
                <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>
              </Assign>
              <WriteLine Text="[Incident_Escalation] INFO: Logging Level 1 incident for monitoring" />
              <!-- TODO: Add log to monitoring dashboard -->
            </Sequence>
          </If.Else>
        </If>
      </If.Else>
    </If>

    <!-- Step 4: Record actions taken -->
    <InvokeMethod MethodName="Add" TargetObject="[v_ActionList]">
      <InvokeMethod.Parameters>
        <InArgument x:TypeArguments="x:String">["Escalation record created: " + v_EscalationId]</InArgument>
      </InvokeMethod.Parameters>
    </InvokeMethod>
    <InvokeMethod MethodName="Add" TargetObject="[v_ActionList]">
      <InvokeMethod.Parameters>
        <InArgument x:TypeArguments="x:String">["Level " + v_EscalationLevel.ToString() + " notifications dispatched"]</InArgument>
      </InvokeMethod.Parameters>
    </InvokeMethod>

    <!-- Step 5: Set notification count based on level -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_NotificationCount]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_EscalationLevel * 2]</InArgument></Assign.Value>
    </Assign>

    <!-- Step 6: Set output arguments -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_EscalationId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_EscalationId]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_EscalationLevel]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_EscalationLevel]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_NotificationsSent]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_NotificationCount]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="scg:List(x:String)">[out_ActionsTaken]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="scg:List(x:String)">[v_ActionList]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_EstimatedResolutionMinutes]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_EscalationLevel * 15]</InArgument></Assign.Value>
    </Assign>

    <WriteLine Text="[Incident_Escalation] Complete — EscalationId={v_EscalationId} Level={v_EscalationLevel}" />
  </Sequence>
</Activity>'''

_XAML_APPROVAL_CHAIN = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sap2020"
    x:Class="MaestroCity.Approval_Chain"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"
    xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
    xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
    xmlns:sap2020="http://schemas.microsoft.com/netfx/2020/xaml/activities/presentation"
    xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <!-- Input Arguments -->
    <x:Property Name="in_RequestType" Type="InArgument(x:String)" />
    <x:Property Name="in_RequestedBy" Type="InArgument(x:String)" />
    <x:Property Name="in_TargetBuildingId" Type="InArgument(x:String)" />
    <x:Property Name="in_ActionDescription" Type="InArgument(x:String)" />
    <x:Property Name="in_RiskLevel" Type="InArgument(x:String)" />
    <x:Property Name="in_AutoApproveThreshold" Type="InArgument(x:Double)" />
    <!-- Output Arguments -->
    <x:Property Name="out_ApprovalId" Type="OutArgument(x:String)" />
    <x:Property Name="out_ApprovalStatus" Type="OutArgument(x:String)" />
    <x:Property Name="out_ApprovedBy" Type="OutArgument(x:String)" />
    <x:Property Name="out_ApprovalTimestampUtc" Type="OutArgument(x:String)" />
    <x:Property Name="out_AuditTrailJson" Type="OutArgument(x:String)" />
  </x:Members>
  <mva:VisualBasic.Settings>
    <mva:VisualBasicSettings>
      <mva:VisualBasicSettings.ImportedNamespaces>
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System" />
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System.Collections.Generic" />
      </mva:VisualBasicSettings.ImportedNamespaces>
    </mva:VisualBasicSettings>
  </mva:VisualBasic.Settings>
  <Sequence DisplayName="Approval Chain — Main">
    <Sequence.Variables>
      <Variable Name="v_ApprovalId" Type="x:String" />
      <Variable Name="v_ApprovalStatus" Type="x:String" Default="[&quot;Pending&quot;]" />
      <Variable Name="v_ApprovedBy" Type="x:String" Default="[&quot;system&quot;]" />
      <Variable Name="v_AuditEntries" Type="scg:List(x:String)" Default="[New List(Of String)]" />
      <Variable Name="v_IsAutoApprove" Type="x:Boolean" Default="[False]" />
    </Sequence.Variables>

    <WriteLine Text="[Approval_Chain] Request received: type={in_RequestType.Get(context)} risk={in_RiskLevel.Get(context)}" />

    <!-- Generate approval ID -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[v_ApprovalId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["APR-" + DateTime.Now.ToString("yyyyMMddHHmmss")]</InArgument></Assign.Value>
    </Assign>

    <!-- Log initial audit entry -->
    <InvokeMethod MethodName="Add" TargetObject="[v_AuditEntries]">
      <InvokeMethod.Parameters>
        <InArgument x:TypeArguments="x:String">[DateTime.UtcNow.ToString("o") + " | REQUEST | type=" + in_RequestType.Get(context) + " requestedBy=" + in_RequestedBy.Get(context)]</InArgument>
      </InvokeMethod.Parameters>
    </InvokeMethod>

    <!-- Determine if auto-approval applies (low-risk or below threshold) -->
    <If Condition="[in_RiskLevel.Get(context) = &quot;low&quot; AndAlso in_AutoApproveThreshold.Get(context) &gt; 0]">
      <If.Then>
        <Sequence DisplayName="Auto-Approve Low Risk">
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Boolean">[v_IsAutoApprove]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Boolean">[True]</InArgument></Assign.Value>
          </Assign>
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:String">[v_ApprovalStatus]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:String">["Approved"]</InArgument></Assign.Value>
          </Assign>
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:String">[v_ApprovedBy]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:String">["VERITAS-AutoApproval"]</InArgument></Assign.Value>
          </Assign>
          <WriteLine Text="[Approval_Chain] Auto-approved (low risk): {v_ApprovalId}" />
        </Sequence>
      </If.Then>
      <If.Else>
        <Sequence DisplayName="Human Approval Required">
          <WriteLine Text="[Approval_Chain] Human approval required for risk level: {in_RiskLevel.Get(context)}" />
          <!-- TODO: Create UiPath Action Center task for human approval -->
          <!-- TODO: Send email notification to approver group -->
          <!-- TODO: Wait for approval with timeout (SLA enforcement) -->
          <!-- TODO: On timeout, auto-escalate to next approver -->
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:String">[v_ApprovalStatus]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:String">["Approved"]</InArgument></Assign.Value>
          </Assign>
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:String">[v_ApprovedBy]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:String">["operations-manager@hospital.org"]</InArgument></Assign.Value>
          </Assign>
        </Sequence>
      </If.Else>
    </If>

    <!-- Append final audit entry -->
    <InvokeMethod MethodName="Add" TargetObject="[v_AuditEntries]">
      <InvokeMethod.Parameters>
        <InArgument x:TypeArguments="x:String">[DateTime.UtcNow.ToString("o") + " | DECISION | status=" + v_ApprovalStatus + " approvedBy=" + v_ApprovedBy]</InArgument>
      </InvokeMethod.Parameters>
    </InvokeMethod>

    <!-- Set outputs -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ApprovalId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_ApprovalId]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ApprovalStatus]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_ApprovalStatus]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ApprovedBy]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_ApprovedBy]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ApprovalTimestampUtc]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[DateTime.UtcNow.ToString("o")]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_AuditTrailJson]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["[" + String.Join(",", v_AuditEntries.Select(Function(e) Chr(34) + e + Chr(34)).ToArray()) + "]"]</InArgument></Assign.Value>
    </Assign>

    <WriteLine Text="[Approval_Chain] Complete — {v_ApprovalId}: {v_ApprovalStatus} by {v_ApprovedBy}" />
  </Sequence>
</Activity>'''

_XAML_CRISIS_RESPONSE = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sap2020"
    x:Class="MaestroCity.Crisis_Response"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"
    xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
    xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
    xmlns:sap2020="http://schemas.microsoft.com/netfx/2020/xaml/activities/presentation"
    xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <!-- Input Arguments -->
    <x:Property Name="in_CrisisType" Type="InArgument(x:String)" />
    <x:Property Name="in_AffectedBuildingIds" Type="InArgument(x:String)" />
    <x:Property Name="in_OperationalStability" Type="InArgument(x:Double)" />
    <x:Property Name="in_ServiceAvailability" Type="InArgument(x:Double)" />
    <x:Property Name="in_HumanStrain" Type="InArgument(x:Double)" />
    <x:Property Name="in_ActivateFailover" Type="InArgument(x:Boolean)" />
    <!-- Output Arguments -->
    <x:Property Name="out_ResponseId" Type="OutArgument(x:String)" />
    <x:Property Name="out_FailoverActivated" Type="OutArgument(x:Boolean)" />
    <x:Property Name="out_StaffingAdjusted" Type="OutArgument(x:Boolean)" />
    <x:Property Name="out_ExternalServicesNotified" Type="OutArgument(x:Boolean)" />
    <x:Property Name="out_RecoveryPlanJson" Type="OutArgument(x:String)" />
    <x:Property Name="out_EstimatedRecoveryMinutes" Type="OutArgument(x:Int32)" />
  </x:Members>
  <mva:VisualBasic.Settings>
    <mva:VisualBasicSettings>
      <mva:VisualBasicSettings.ImportedNamespaces>
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System" />
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System.Collections.Generic" />
      </mva:VisualBasicSettings.ImportedNamespaces>
    </mva:VisualBasicSettings>
  </mva:VisualBasic.Settings>
  <Sequence DisplayName="Crisis Response — Main">
    <Sequence.Variables>
      <Variable Name="v_ResponseId" Type="x:String" />
      <Variable Name="v_FailoverDone" Type="x:Boolean" Default="[False]" />
      <Variable Name="v_StaffingDone" Type="x:Boolean" Default="[False]" />
      <Variable Name="v_ExternalNotified" Type="x:Boolean" Default="[False]" />
      <Variable Name="v_EstimatedRecovery" Type="x:Int32" Default="[30]" />
      <Variable Name="v_RecoverySteps" Type="scg:List(x:String)" Default="[New List(Of String)]" />
    </Sequence.Variables>

    <WriteLine Text="[Crisis_Response] CRISIS ACTIVATED — type={in_CrisisType.Get(context)} stability={in_OperationalStability.Get(context)}" />

    <!-- Generate response ID -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[v_ResponseId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["CR-" + DateTime.Now.ToString("yyyyMMddHHmmss")]</InArgument></Assign.Value>
    </Assign>

    <!-- Phase 1: Immediate failover if requested or stability is critical -->
    <If Condition="[in_ActivateFailover.Get(context) OrElse in_OperationalStability.Get(context) &lt; 25]">
      <If.Then>
        <Sequence DisplayName="Activate Failover Infrastructure">
          <WriteLine Text="[Crisis_Response] Activating backup infrastructure failover" />
          <!-- TODO: Call internal failover activation API -->
          <!-- TODO: Verify DNS cutover to backup endpoints -->
          <!-- TODO: Validate backup health before routing traffic -->
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Boolean">[v_FailoverDone]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Boolean">[True]</InArgument></Assign.Value>
          </Assign>
          <InvokeMethod MethodName="Add" TargetObject="[v_RecoverySteps]">
            <InvokeMethod.Parameters>
              <InArgument x:TypeArguments="x:String">["Backup infrastructure failover activated"]</InArgument>
            </InvokeMethod.Parameters>
          </InvokeMethod>
        </Sequence>
      </If.Then>
    </If>

    <!-- Phase 2: Emergency staffing if human strain is high -->
    <If Condition="[in_HumanStrain.Get(context) &gt; 70]">
      <If.Then>
        <Sequence DisplayName="Emergency Staffing Adjustment">
          <WriteLine Text="[Crisis_Response] Human strain critical — triggering emergency staffing protocol" />
          <!-- TODO: Send on-call paging to backup staff roster -->
          <!-- TODO: Invoke Emergency_Staffing subprocess -->
          <!-- TODO: Update workforce management system -->
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Boolean">[v_StaffingDone]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Boolean">[True]</InArgument></Assign.Value>
          </Assign>
          <InvokeMethod MethodName="Add" TargetObject="[v_RecoverySteps]">
            <InvokeMethod.Parameters>
              <InArgument x:TypeArguments="x:String">["Emergency staffing protocol activated — on-call staff notified"]</InArgument>
            </InvokeMethod.Parameters>
          </InvokeMethod>
        </Sequence>
      </If.Then>
    </If>

    <!-- Phase 3: Notify external services if service availability is critically low -->
    <If Condition="[in_ServiceAvailability.Get(context) &lt; 40]">
      <If.Then>
        <Sequence DisplayName="External Service Notification">
          <WriteLine Text="[Crisis_Response] Service availability critical — notifying external partners and patients" />
          <!-- TODO: Send SMS/email to affected patient population via communication hub -->
          <!-- TODO: Update external status page (StatusPage.io or equivalent) -->
          <!-- TODO: Notify regulatory bodies if downtime exceeds SLA threshold -->
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Boolean">[v_ExternalNotified]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Boolean">[True]</InArgument></Assign.Value>
          </Assign>
          <InvokeMethod MethodName="Add" TargetObject="[v_RecoverySteps]">
            <InvokeMethod.Parameters>
              <InArgument x:TypeArguments="x:String">["External stakeholders notified — status page updated"]</InArgument>
            </InvokeMethod.Parameters>
          </InvokeMethod>
        </Sequence>
      </If.Then>
    </If>

    <!-- Calculate estimated recovery time -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_EstimatedRecovery]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[CInt(Math.Ceiling((100 - in_OperationalStability.Get(context)) / 5))]</InArgument></Assign.Value>
    </Assign>

    <!-- Set output arguments -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ResponseId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_ResponseId]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Boolean">[out_FailoverActivated]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Boolean">[v_FailoverDone]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Boolean">[out_StaffingAdjusted]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Boolean">[v_StaffingDone]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Boolean">[out_ExternalServicesNotified]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Boolean">[v_ExternalNotified]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_EstimatedRecoveryMinutes]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_EstimatedRecovery]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_RecoveryPlanJson]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["{ &quot;responseId&quot;: &quot;" + v_ResponseId + "&quot;, &quot;steps&quot;: " + v_RecoverySteps.Count.ToString() + ", &quot;estimatedMinutes&quot;: " + v_EstimatedRecovery.ToString() + " }"]</InArgument></Assign.Value>
    </Assign>

    <WriteLine Text="[Crisis_Response] Complete — {v_ResponseId} estimatedRecovery={v_EstimatedRecovery}min" />
  </Sequence>
</Activity>'''

_XAML_EMERGENCY_STAFFING = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sap2020"
    x:Class="MaestroCity.Emergency_Staffing"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"
    xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
    xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
    xmlns:sap2020="http://schemas.microsoft.com/netfx/2020/xaml/activities/presentation"
    xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <!-- Input Arguments -->
    <x:Property Name="in_TargetBuildingId" Type="InArgument(x:String)" />
    <x:Property Name="in_TargetBuildingName" Type="InArgument(x:String)" />
    <x:Property Name="in_CurrentStaffingLevel" Type="InArgument(x:Double)" />
    <x:Property Name="in_RequestedStaffingLevel" Type="InArgument(x:Double)" />
    <x:Property Name="in_HumanStrain" Type="InArgument(x:Double)" />
    <x:Property Name="in_UrgencyLevel" Type="InArgument(x:String)" />
    <!-- Output Arguments -->
    <x:Property Name="out_RequestId" Type="OutArgument(x:String)" />
    <x:Property Name="out_StaffAllocated" Type="OutArgument(x:Int32)" />
    <x:Property Name="out_NewStaffingLevel" Type="OutArgument(x:Double)" />
    <x:Property Name="out_NotifiedRoles" Type="OutArgument(scg:List(x:String))" />
    <x:Property Name="out_ExpectedArrivalMinutes" Type="OutArgument(x:Int32)" />
  </x:Members>
  <mva:VisualBasic.Settings>
    <mva:VisualBasicSettings>
      <mva:VisualBasicSettings.ImportedNamespaces>
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System" />
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System.Collections.Generic" />
      </mva:VisualBasicSettings.ImportedNamespaces>
    </mva:VisualBasicSettings>
  </mva:VisualBasic.Settings>
  <Sequence DisplayName="Emergency Staffing — Main">
    <Sequence.Variables>
      <Variable Name="v_RequestId" Type="x:String" />
      <Variable Name="v_StaffCount" Type="x:Int32" Default="[0]" />
      <Variable Name="v_NewLevel" Type="x:Double" Default="[0.0]" />
      <Variable Name="v_NotifiedRoles" Type="scg:List(x:String)" Default="[New List(Of String)]" />
      <Variable Name="v_ArrivalMinutes" Type="x:Int32" Default="[15]" />
    </Sequence.Variables>

    <WriteLine Text="[Emergency_Staffing] Request for {in_TargetBuildingName.Get(context)}: current={in_CurrentStaffingLevel.Get(context)}% requested={in_RequestedStaffingLevel.Get(context)}%" />

    <!-- Generate request ID -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[v_RequestId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["STAFF-" + DateTime.Now.ToString("yyyyMMddHHmmss") + "-" + in_TargetBuildingId.Get(context)]</InArgument></Assign.Value>
    </Assign>

    <!-- Calculate staff needed -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_StaffCount]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[CInt(Math.Ceiling((in_RequestedStaffingLevel.Get(context) - in_CurrentStaffingLevel.Get(context)) / 10))]</InArgument></Assign.Value>
    </Assign>

    <!-- Notify roles based on urgency -->
    <If Condition="[in_UrgencyLevel.Get(context) = &quot;critical&quot; OrElse in_HumanStrain.Get(context) &gt; 85]">
      <If.Then>
        <Sequence DisplayName="Critical Urgency — All Available Staff">
          <InvokeMethod MethodName="Add" TargetObject="[v_NotifiedRoles]">
            <InvokeMethod.Parameters>
              <InArgument x:TypeArguments="x:String">["on-call-primary"]</InArgument>
            </InvokeMethod.Parameters>
          </InvokeMethod>
          <InvokeMethod MethodName="Add" TargetObject="[v_NotifiedRoles]">
            <InvokeMethod.Parameters>
              <InArgument x:TypeArguments="x:String">["on-call-secondary"]</InArgument>
            </InvokeMethod.Parameters>
          </InvokeMethod>
          <InvokeMethod MethodName="Add" TargetObject="[v_NotifiedRoles]">
            <InvokeMethod.Parameters>
              <InArgument x:TypeArguments="x:String">["supervisor-emergency"]</InArgument>
            </InvokeMethod.Parameters>
          </InvokeMethod>
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_ArrivalMinutes]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Int32">[5]</InArgument></Assign.Value>
          </Assign>
          <WriteLine Text="[Emergency_Staffing] CRITICAL: All on-call staff paged, supervisor alerted" />
          <!-- TODO: Trigger mass notification via hospital communication system -->
          <!-- TODO: Update HR system with emergency callout record -->
        </Sequence>
      </If.Then>
      <If.Else>
        <Sequence DisplayName="Standard Urgency — Primary On-Call">
          <InvokeMethod MethodName="Add" TargetObject="[v_NotifiedRoles]">
            <InvokeMethod.Parameters>
              <InArgument x:TypeArguments="x:String">["on-call-primary"]</InArgument>
            </InvokeMethod.Parameters>
          </InvokeMethod>
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_ArrivalMinutes]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Int32">[15]</InArgument></Assign.Value>
          </Assign>
          <WriteLine Text="[Emergency_Staffing] Standard: primary on-call staff paged" />
          <!-- TODO: Send SMS to on-call roster -->
          <!-- TODO: Log in shift management system -->
        </Sequence>
      </If.Else>
    </If>

    <!-- Calculate new staffing level -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Double">[v_NewLevel]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Double">[Math.Min(100.0, in_CurrentStaffingLevel.Get(context) + (v_StaffCount * 10.0))]</InArgument></Assign.Value>
    </Assign>

    <!-- Set outputs -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_RequestId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_RequestId]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_StaffAllocated]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_StaffCount]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Double">[out_NewStaffingLevel]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Double">[v_NewLevel]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="scg:List(x:String)">[out_NotifiedRoles]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="scg:List(x:String)">[v_NotifiedRoles]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_ExpectedArrivalMinutes]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_ArrivalMinutes]</InArgument></Assign.Value>
    </Assign>

    <WriteLine Text="[Emergency_Staffing] Complete — {v_RequestId}: allocated {v_StaffCount} staff, new level={v_NewLevel}%, ETA={v_ArrivalMinutes}min" />
  </Sequence>
</Activity>'''

_XAML_TRUST_RECOVERY = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sap2020"
    x:Class="MaestroCity.Trust_Recovery_Protocol"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"
    xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
    xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
    xmlns:sap2020="http://schemas.microsoft.com/netfx/2020/xaml/activities/presentation"
    xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members>
    <!-- Input Arguments -->
    <x:Property Name="in_BuildingId" Type="InArgument(x:String)" />
    <x:Property Name="in_BuildingName" Type="InArgument(x:String)" />
    <x:Property Name="in_CurrentTrustScore" Type="InArgument(x:Double)" />
    <x:Property Name="in_CurrentSystemTrust" Type="InArgument(x:Double)" />
    <x:Property Name="in_AgentId" Type="InArgument(x:String)" />
    <x:Property Name="in_IncidentRootCause" Type="InArgument(x:String)" />
    <!-- Output Arguments -->
    <x:Property Name="out_ProtocolId" Type="OutArgument(x:String)" />
    <x:Property Name="out_RecoveryStepsCompleted" Type="OutArgument(x:Int32)" />
    <x:Property Name="out_TrustRestoredTo" Type="OutArgument(x:Double)" />
    <x:Property Name="out_AutonomyRecommendation" Type="OutArgument(x:Int32)" />
    <x:Property Name="out_PostIncidentReportUrl" Type="OutArgument(x:String)" />
    <x:Property Name="out_RecoveryVerified" Type="OutArgument(x:Boolean)" />
  </x:Members>
  <mva:VisualBasic.Settings>
    <mva:VisualBasicSettings>
      <mva:VisualBasicSettings.ImportedNamespaces>
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System" />
        <mva:VisualBasicImportReference Assembly="mscorlib" Import="System.Collections.Generic" />
      </mva:VisualBasicSettings.ImportedNamespaces>
    </mva:VisualBasicSettings>
  </mva:VisualBasic.Settings>
  <Sequence DisplayName="Trust Recovery Protocol — Main">
    <Sequence.Variables>
      <Variable Name="v_ProtocolId" Type="x:String" />
      <Variable Name="v_StepsCompleted" Type="x:Int32" Default="[0]" />
      <Variable Name="v_TrustTarget" Type="x:Double" Default="[75.0]" />
      <Variable Name="v_AutonomyRec" Type="x:Int32" Default="[1]" />
      <Variable Name="v_ReportUrl" Type="x:String" />
      <Variable Name="v_Verified" Type="x:Boolean" Default="[False]" />
    </Sequence.Variables>

    <WriteLine Text="[Trust_Recovery_Protocol] Initiating trust recovery for {in_BuildingName.Get(context)}: trustScore={in_CurrentTrustScore.Get(context)} systemTrust={in_CurrentSystemTrust.Get(context)}" />

    <!-- Generate protocol ID -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[v_ProtocolId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["TRP-" + DateTime.Now.ToString("yyyyMMddHHmmss") + "-" + in_BuildingId.Get(context)]</InArgument></Assign.Value>
    </Assign>

    <!-- Step 1: Reduce agent autonomy temporarily for trust recovery -->
    <If Condition="[in_CurrentSystemTrust.Get(context) &lt; 40]">
      <If.Then>
        <Sequence DisplayName="Severe Trust Loss — Reduce to Level 0">
          <Assign>
            <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_AutonomyRec]</OutArgument></Assign.To>
            <Assign.Value><InArgument x:TypeArguments="x:Int32">[0]</InArgument></Assign.Value>
          </Assign>
          <WriteLine Text="[Trust_Recovery_Protocol] Severe trust loss — recommending autonomy reduction to Level 0 (full human oversight)" />
          <!-- TODO: Apply autonomy override to all agents via API -->
          <!-- TODO: Alert compliance officer of trust breach -->
        </Sequence>
      </If.Then>
      <If.Else>
        <If Condition="[in_CurrentSystemTrust.Get(context) &lt; 60]">
          <If.Then>
            <Sequence DisplayName="Moderate Trust Loss — Reduce to Level 1">
              <Assign>
                <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_AutonomyRec]</OutArgument></Assign.To>
                <Assign.Value><InArgument x:TypeArguments="x:Int32">[1]</InArgument></Assign.Value>
              </Assign>
              <WriteLine Text="[Trust_Recovery_Protocol] Moderate trust loss — recommending autonomy reduction to Level 1" />
            </Sequence>
          </If.Then>
          <If.Else>
            <Sequence DisplayName="Minor Trust Loss — Maintain Level 2">
              <Assign>
                <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_AutonomyRec]</OutArgument></Assign.To>
                <Assign.Value><InArgument x:TypeArguments="x:Int32">[2]</InArgument></Assign.Value>
              </Assign>
              <WriteLine Text="[Trust_Recovery_Protocol] Minor trust loss — maintaining Level 2 with enhanced monitoring" />
            </Sequence>
          </If.Else>
        </If>
      </If.Else>
    </If>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_StepsCompleted]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_StepsCompleted + 1]</InArgument></Assign.Value>
    </Assign>

    <!-- Step 2: Run diagnostic verification -->
    <WriteLine Text="[Trust_Recovery_Protocol] Running system diagnostic for {in_BuildingId.Get(context)}" />
    <!-- TODO: Execute diagnostic script against building health check API -->
    <!-- TODO: Verify all dependent systems are healthy -->
    <!-- TODO: Confirm no latent failures remain -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_StepsCompleted]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_StepsCompleted + 1]</InArgument></Assign.Value>
    </Assign>

    <!-- Step 3: Gradual trust rebuild schedule -->
    <WriteLine Text="[Trust_Recovery_Protocol] Scheduling trust rebuild: +5 points per successful operation, monitored for 10 cycles" />
    <!-- TODO: Register trust rebuild schedule in monitoring system -->
    <!-- TODO: Set alert threshold for trust deviation during recovery -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Double">[v_TrustTarget]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Double">[Math.Min(100.0, in_CurrentTrustScore.Get(context) + 25.0)]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_StepsCompleted]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_StepsCompleted + 1]</InArgument></Assign.Value>
    </Assign>

    <!-- Step 4: Generate post-incident report -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[v_ReportUrl]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">["https://confluence.hospital.org/incidents/" + v_ProtocolId]</InArgument></Assign.Value>
    </Assign>
    <WriteLine Text="[Trust_Recovery_Protocol] Post-incident report URL: {v_ReportUrl}" />
    <!-- TODO: Create Confluence page with incident timeline -->
    <!-- TODO: Schedule 5-day follow-up review meeting -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[v_StepsCompleted]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_StepsCompleted + 1]</InArgument></Assign.Value>
    </Assign>

    <!-- Mark as verified if all steps completed -->
    <If Condition="[v_StepsCompleted &gt;= 4]">
      <If.Then>
        <Assign>
          <Assign.To><OutArgument x:TypeArguments="x:Boolean">[v_Verified]</OutArgument></Assign.To>
          <Assign.Value><InArgument x:TypeArguments="x:Boolean">[True]</InArgument></Assign.Value>
        </Assign>
      </If.Then>
    </If>

    <!-- Set output arguments -->
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_ProtocolId]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_ProtocolId]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_RecoveryStepsCompleted]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_StepsCompleted]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Double">[out_TrustRestoredTo]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Double">[v_TrustTarget]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Int32">[out_AutonomyRecommendation]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Int32">[v_AutonomyRec]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:String">[out_PostIncidentReportUrl]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:String">[v_ReportUrl]</InArgument></Assign.Value>
    </Assign>
    <Assign>
      <Assign.To><OutArgument x:TypeArguments="x:Boolean">[out_RecoveryVerified]</OutArgument></Assign.To>
      <Assign.Value><InArgument x:TypeArguments="x:Boolean">[v_Verified]</InArgument></Assign.Value>
    </Assign>

    <WriteLine Text="[Trust_Recovery_Protocol] Complete — {v_ProtocolId}: steps={v_StepsCompleted} trustTarget={v_TrustTarget} autonomyRec={v_AutonomyRec}" />
  </Sequence>
</Activity>'''


_PROCESS_METADATA = {
    "Incident_Escalation": {
        "description": (
            "Receives an incident report from SENTINEL (Incident Response Agent) and routes "
            "it through the correct escalation chain based on severity and operational stability. "
            "Sends notifications, creates tracking records, and returns escalation ID and level."
        ),
        "input_args": [
            ("in_BuildingId", "String", "ID of the affected building"),
            ("in_BuildingName", "String", "Human-readable building name"),
            ("in_Severity", "String", "'info' | 'warning' | 'critical'"),
            ("in_OperationalStability", "Double", "Current operational stability 0-100"),
            ("in_AffectedWorkflows", "Int32", "Number of workflows impacted"),
        ],
        "output_args": [
            ("out_EscalationId", "String", "Unique escalation tracking ID"),
            ("out_EscalationLevel", "Int32", "Escalation level 1-3"),
            ("out_NotificationsSent", "Int32", "Number of notifications dispatched"),
            ("out_ActionsTaken", "List(String)", "List of actions performed"),
            ("out_EstimatedResolutionMinutes", "Int32", "Estimated time to resolution"),
        ],
        "integrations": ["PagerDuty", "ServiceNow", "UiPath Action Center"],
        "xaml": _XAML_INCIDENT_ESCALATION,
        "download_filename": "Incident_Escalation.xaml",
    },
    "Approval_Chain": {
        "description": (
            "Manages multi-level approval workflows for high-risk operational changes. "
            "VERITAS (Compliance Agent) triggers this process when an action requires "
            "human sign-off. Supports auto-approval for low-risk actions and full "
            "UiPath Action Center human-in-the-loop for high-risk changes."
        ),
        "input_args": [
            ("in_RequestType", "String", "Type of approval requested"),
            ("in_RequestedBy", "String", "Agent ID or user requesting approval"),
            ("in_TargetBuildingId", "String", "Building affected by the change"),
            ("in_ActionDescription", "String", "Human-readable description of proposed action"),
            ("in_RiskLevel", "String", "'low' | 'medium' | 'high'"),
            ("in_AutoApproveThreshold", "Double", "Stability threshold for auto-approval (0 = never auto-approve)"),
        ],
        "output_args": [
            ("out_ApprovalId", "String", "Unique approval record ID"),
            ("out_ApprovalStatus", "String", "'Approved' | 'Rejected' | 'Timeout'"),
            ("out_ApprovedBy", "String", "Approver identity"),
            ("out_ApprovalTimestampUtc", "String", "ISO 8601 timestamp of decision"),
            ("out_AuditTrailJson", "String", "JSON audit log of approval chain"),
        ],
        "integrations": ["UiPath Action Center", "Active Directory", "JIRA"],
        "xaml": _XAML_APPROVAL_CHAIN,
        "download_filename": "Approval_Chain.xaml",
    },
    "Crisis_Response": {
        "description": (
            "Coordinates the full crisis response playbook when operational stability drops "
            "below critical thresholds. Triggered by APEX (Executive Strategy Agent) during "
            "crisis or collapsed phases. Orchestrates failover activation, emergency staffing, "
            "and external stakeholder notifications in the correct sequence."
        ),
        "input_args": [
            ("in_CrisisType", "String", "'infrastructure' | 'staffing' | 'cascade' | 'unknown'"),
            ("in_AffectedBuildingIds", "String", "Comma-separated list of affected building IDs"),
            ("in_OperationalStability", "Double", "Current operational stability 0-100"),
            ("in_ServiceAvailability", "Double", "Current service availability 0-100"),
            ("in_HumanStrain", "Double", "Current human strain 0-100"),
            ("in_ActivateFailover", "Boolean", "Whether to immediately activate failover infrastructure"),
        ],
        "output_args": [
            ("out_ResponseId", "String", "Unique crisis response ID"),
            ("out_FailoverActivated", "Boolean", "Whether failover was activated"),
            ("out_StaffingAdjusted", "Boolean", "Whether emergency staffing was triggered"),
            ("out_ExternalServicesNotified", "Boolean", "Whether external partners were notified"),
            ("out_RecoveryPlanJson", "String", "JSON summary of recovery plan"),
            ("out_EstimatedRecoveryMinutes", "Int32", "Estimated time to recovery"),
        ],
        "integrations": ["Emergency_Staffing", "PagerDuty", "StatusPage.io", "SMS Gateway"],
        "xaml": _XAML_CRISIS_RESPONSE,
        "download_filename": "Crisis_Response.xaml",
    },
    "Emergency_Staffing": {
        "description": (
            "Pages on-call staff and adjusts staffing allocations for a specific building "
            "during emergency conditions. Triggered by ARIA (Operations Coordinator) when "
            "human strain exceeds thresholds or a building's staffing level drops critically. "
            "Integrates with HR systems and workforce management platforms."
        ),
        "input_args": [
            ("in_TargetBuildingId", "String", "Building requiring additional staff"),
            ("in_TargetBuildingName", "String", "Human-readable building name"),
            ("in_CurrentStaffingLevel", "Double", "Current staffing level 0-100"),
            ("in_RequestedStaffingLevel", "Double", "Target staffing level 0-100"),
            ("in_HumanStrain", "Double", "Current human strain metric 0-100"),
            ("in_UrgencyLevel", "String", "'standard' | 'urgent' | 'critical'"),
        ],
        "output_args": [
            ("out_RequestId", "String", "Unique staffing request ID"),
            ("out_StaffAllocated", "Int32", "Number of additional staff allocated"),
            ("out_NewStaffingLevel", "Double", "Projected new staffing level after allocation"),
            ("out_NotifiedRoles", "List(String)", "List of roles/teams notified"),
            ("out_ExpectedArrivalMinutes", "Int32", "Expected time until staff are on-site"),
        ],
        "integrations": ["Kronos Workforce", "SMS Gateway", "HR Information System"],
        "xaml": _XAML_EMERGENCY_STAFFING,
        "download_filename": "Emergency_Staffing.xaml",
    },
    "Trust_Recovery_Protocol": {
        "description": (
            "Executes the structured trust recovery protocol after automation failures or "
            "decisions that eroded system trust. Triggered by VERITAS (Compliance Agent) "
            "when systemTrust or buildingTrustLevel drops below thresholds. Temporarily "
            "reduces agent autonomy, runs diagnostics, schedules gradual trust rebuilding, "
            "and produces post-incident documentation."
        ),
        "input_args": [
            ("in_BuildingId", "String", "Building where trust was lost"),
            ("in_BuildingName", "String", "Human-readable building name"),
            ("in_CurrentTrustScore", "Double", "Building's current trust level 0-100"),
            ("in_CurrentSystemTrust", "Double", "Overall system trust metric 0-100"),
            ("in_AgentId", "String", "Agent whose action caused trust drop (if applicable)"),
            ("in_IncidentRootCause", "String", "Description of what caused trust erosion"),
        ],
        "output_args": [
            ("out_ProtocolId", "String", "Unique protocol execution ID"),
            ("out_RecoveryStepsCompleted", "Int32", "Number of recovery steps completed"),
            ("out_TrustRestoredTo", "Double", "Target trust level after recovery"),
            ("out_AutonomyRecommendation", "Int32", "Recommended autonomy level 0-4 during recovery"),
            ("out_PostIncidentReportUrl", "String", "URL to post-incident report document"),
            ("out_RecoveryVerified", "Boolean", "Whether all recovery steps completed successfully"),
        ],
        "integrations": ["Confluence", "Active Directory", "Monitoring Dashboard"],
        "xaml": _XAML_TRUST_RECOVERY,
        "download_filename": "Trust_Recovery_Protocol.xaml",
    },
}


def _make_project_json(process_name: str) -> dict:
    return {
        "name": process_name,
        "description": _PROCESS_METADATA[process_name]["description"],
        "projectVersion": "1.0.0",
        "runtimeOptions": {
            "uiAutomationDisabled": True,
            "requiresUserInteraction": False,
            "supportsPersistence": False,
            "excludedLoggedData": [],
        },
        "targetFramework": "Portable",
        "designOptions": {
            "outputType": "Process",
            "timeline": False,
            "expressionLanguage": "VisualBasic",
        },
        "dependencies": {
            "UiPath.System.Activities": "[22.10.4, )",
            "UiPath.Excel.Activities": "[2.16.1, )",
        },
        "webSettings": {
            "nuGetServerUrl": "https://www.myget.org/F/workflow/",
            "activitiesFeed": "https://pkgs.dev.azure.com/uipath/Public.Feeds/_packaging/UiPath-Official/nuget/v3/index.json",
        },
        "generatedBy": "Maestro City Simulation",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scenarioValidated": True,
    }


def _make_readme(process_name: str) -> str:
    meta = _PROCESS_METADATA[process_name]
    lines = [
        f"# {process_name}",
        f"",
        f"> **Generated by Maestro City** — scenario-validated UiPath process template",
        f"",
        f"## Description",
        f"",
        meta["description"],
        f"",
        f"## Input Arguments",
        f"",
        f"| Argument | Type | Description |",
        f"|----------|------|-------------|",
    ]
    for name, arg_type, desc in meta["input_args"]:
        lines.append(f"| `{name}` | `{arg_type}` | {desc} |")
    lines += [
        f"",
        f"## Output Arguments",
        f"",
        f"| Argument | Type | Description |",
        f"|----------|------|-------------|",
    ]
    for name, arg_type, desc in meta["output_args"]:
        lines.append(f"| `{name}` | `{arg_type}` | {desc} |")
    lines += [
        f"",
        f"## Integrations",
        f"",
    ]
    for integration in meta["integrations"]:
        lines.append(f"- {integration}")
    lines += [
        f"",
        f"## Setup Instructions",
        f"",
        f"1. Open UiPath Studio and import this project folder",
        f"2. Review all `<!-- TODO: -->` comments in `Main.xaml` and implement real integration calls",
        f"3. Configure connection strings and API credentials in `appsettings.json`",
        f"4. Test in UiPath Studio Test Manager before publishing to Orchestrator",
        f"5. Publish to your Orchestrator tenant under the `MaestroCity` folder",
        f"",
        f"## Triggering from Maestro City",
        f"",
        f"This process is triggered via the UiPath Orchestrator Jobs API:",
        f"",
        f"```json",
        f'{{',
        f'  "startInfo": {{',
        f'    "ReleaseKey": "<your-release-key>",',
        f'    "Strategy": "JobsCount",',
        f'    "JobsCount": 1,',
        f'    "InputArguments": {{',
    ]
    for name, arg_type, _ in meta["input_args"][:3]:
        lines.append(f'      "{name}": "<value>",')
    lines += [
        f'    }}',
        f'  }}',
        f'}}',
        f"```",
        f"",
        f"---",
        f"*Generated by Maestro City | UiPath Hackathon Demo | Validate in simulation before production deployment*",
    ]
    return "\n".join(lines)


class ProcessTemplateGenerator:
    """Generates importable UiPath Studio process templates for all 5 Maestro City processes."""

    def generate_all_templates(self) -> Dict[str, Any]:
        """Return templates for all 5 processes."""
        result = {}
        for process_name in _PROCESS_METADATA:
            result[process_name] = self.generate_template(process_name, [])
        return {
            "generatedAt": time.time(),
            "processCount": len(result),
            "processes": result,
        }

    def generate_template(self, process_name: str, job_records: list) -> Dict[str, Any]:
        """Generate a complete template for one process."""
        if process_name not in _PROCESS_METADATA:
            return {
                "error": f"Unknown process: {process_name}. "
                         f"Valid processes: {list(_PROCESS_METADATA.keys())}"
            }

        meta = _PROCESS_METADATA[process_name]
        project_json = _make_project_json(process_name)
        readme = _make_readme(process_name)

        # Add job execution statistics if records provided
        job_stats = None
        if job_records:
            relevant_jobs = [j for j in job_records if j.process_name == process_name]
            if relevant_jobs:
                successful = sum(1 for j in relevant_jobs if j.final_state == "Successful")
                faulted = sum(1 for j in relevant_jobs if j.final_state == "Faulted")
                avg_stability_impact = (
                    sum(j.stability_impact or 0 for j in relevant_jobs) / len(relevant_jobs)
                )
                job_stats = {
                    "totalRuns": len(relevant_jobs),
                    "successful": successful,
                    "faulted": faulted,
                    "successRate": round(successful / len(relevant_jobs) * 100, 1),
                    "averageStabilityImpact": round(avg_stability_impact, 1),
                }

        return {
            "processName": process_name,
            "description": meta["description"],
            "inputArguments": [
                {"name": name, "type": arg_type, "description": desc}
                for name, arg_type, desc in meta["input_args"]
            ],
            "outputArguments": [
                {"name": name, "type": arg_type, "description": desc}
                for name, arg_type, desc in meta["output_args"]
            ],
            "integrations": meta["integrations"],
            "xaml": meta["xaml"],
            "projectJson": project_json,
            "readme": readme,
            "downloadFilename": meta["download_filename"],
            "projectJsonFilename": "project.json",
            "readmeFilename": "README.md",
            "simulationJobStats": job_stats,
            "generatedAt": time.time(),
        }
