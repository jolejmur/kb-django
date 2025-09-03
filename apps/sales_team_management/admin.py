# apps/sales_team_management/admin.py
from django.contrib import admin
from .models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)


# ============================================================
# INLINES FOR NEW MODELS
# ============================================================

class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    fields = ('user', 'position_type', 'is_active', 'start_date')
    readonly_fields = ('created_at',)


class HierarchyRelationInline(admin.TabularInline):
    model = HierarchyRelation
    fk_name = 'supervisor_membership'
    extra = 0
    fields = ('subordinate_membership', 'relation_type', 'is_primary', 'is_active')


class CommissionStructureInline(admin.TabularInline):
    model = CommissionStructure
    extra = 0
    fields = ('structure_name', 'commission_type', 'is_active')


# ============================================================
# ADMIN FOR NEW MODELS
# ============================================================

@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'unit_type', 'is_active', 'total_members', 'created_at')
    list_filter = ('unit_type', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)
    inlines = [TeamMembershipInline, CommissionStructureInline]
    
    def total_members(self, obj):
        return obj.teammembership_set.filter(is_active=True).count()
    
    total_members.short_description = 'Active Members'


@admin.register(PositionType)
class PositionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'hierarchy_level', 'is_active', 'created_at')
    list_filter = ('hierarchy_level', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    ordering = ('hierarchy_level', 'name')


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organizational_unit', 'position_type', 'is_active', 'start_date')
    list_filter = ('organizational_unit', 'position_type', 'is_active', 'start_date')
    search_fields = (
        'user__username', 'user__first_name', 'user__last_name',
        'organizational_unit__name', 'position_type__name'
    )
    ordering = ('-start_date',)
    inlines = [HierarchyRelationInline]
    raw_id_fields = ('user',)


@admin.register(HierarchyRelation)
class HierarchyRelationAdmin(admin.ModelAdmin):
    list_display = (
        'supervisor_user', 'subordinate_user', 'relation_type', 
        'is_primary', 'is_active', 'created_at'
    )
    list_filter = ('relation_type', 'is_primary', 'is_active', 'created_at')
    search_fields = (
        'supervisor_membership__user__username',
        'supervisor_membership__user__first_name',
        'supervisor_membership__user__last_name',
        'subordinate_membership__user__username', 
        'subordinate_membership__user__first_name',
        'subordinate_membership__user__last_name'
    )
    raw_id_fields = ('supervisor_membership', 'subordinate_membership')
    
    def supervisor_user(self, obj):
        return obj.supervisor_membership.user.get_full_name() or obj.supervisor_membership.user.username
    
    def subordinate_user(self, obj):
        return obj.subordinate_membership.user.get_full_name() or obj.subordinate_membership.user.username
    
    supervisor_user.short_description = 'Supervisor'
    subordinate_user.short_description = 'Subordinate'


@admin.register(CommissionStructure)
class CommissionStructureAdmin(admin.ModelAdmin):
    list_display = (
        'structure_name', 'organizational_unit', 'commission_type',
        'total_percentage', 'is_active', 'created_at'
    )
    list_filter = ('commission_type', 'is_active', 'organizational_unit', 'created_at')
    search_fields = ('structure_name', 'organizational_unit__name')
    ordering = ('-created_at',)
    
    def total_percentage(self, obj):
        if obj.position_percentages:
            total = sum(obj.position_percentages.values())
            return f"{total}%"
        return "0%"
    
    total_percentage.short_description = 'Total %'