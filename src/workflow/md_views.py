# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import django_tables2 as tables
from celery.task.control import inspect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, reverse, render
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.translation import ugettext_lazy as _

import action
from action.models import Action
from dataops import ops, pandas_db
from dataops.models import SQLConnection
from dataops.sqlcon_views import SQLConnectionTableAdmin
from logs.models import Log
from ontask.permissions import is_instructor, UserIsInstructor, is_admin
from ontask.tables import OperationsColumn
from .forms import WorkflowForm
from .models import Workflow, Column
from .ops import (get_workflow, store_workflow_in_session)

class WorkflowTable(tables.Table):
    name = tables.Column(verbose_name=_('Name'))

    description_text = tables.Column(
        empty_values=[],
        verbose_name=_('Description')
    )

    nrows_cols = tables.Column(
        empty_values=[],
        verbose_name=_('Rows/Columns'),
        default=_('No data')
    )

    modified = tables.DateTimeColumn(verbose_name=_('Last modified'))

    def __init__(self, data, *args, **kwargs):
        table_id = kwargs.pop('id')

        super(WorkflowTable, self).__init__(data, *args, **kwargs)
        # If an ID was given, pass it on to the table attrs.
        if table_id:
            self.attrs['id'] = table_id

    def render_nrows_cols(self, record):
        if record['nrows'] == 0 and record['ncols'] == 0:
            return "No data"

        return format_html("{0}/{1}".format(record['nrows'], record['ncols']))

    operations = OperationsColumn(
        verbose_name=_('Operations'),
        attrs={'td': {'class': 'dt-body-center'}},
        template_file='workflow/includes/workflow_basic_buttons.html',
        template_context=lambda record: {'workflow': record}
    )

    class Meta:
        model = Workflow

        fields = ('name', 'description_text', 'nrows_cols', 'modified')

        sequence = ('name', 'description_text', 'nrows_cols', 'modified')

        exclude = ('user', 'attributes', 'nrows', 'ncols', 'column_names',
                   'column_types', 'column_unique', 'query_builder_ops',
                   'data_frame_table_name')

        attrs = {
            'class': 'table display table-bordered',
            'id': 'workflow-table'
        }


class WorkflowShareTable(tables.Table):
    email = tables.Column(
        attrs={'td': {'class': 'dt-body-center'}},
        verbose_name=str('User')
    )

    operations = OperationsColumn(
        attrs={'td': {'class': 'dt-body-center'}},
        verbose_name='',
        orderable=False,
        template_file='workflow/includes/partial_share_operations.html',
        template_context=lambda x: {'id': x['id']}
    )

    class Meta:
        fields = ('email', 'id')

        sequence = ('email', 'operations')

        attrs = {
            'class': 'table display',
            'id': 'share-table',
            'th': {'class': 'dt-body-center'}
        }


def save_workflow_form(request, form, template_name):
    # Ajax response. Form is not valid until proven otherwise
    data = {'form_is_valid': False}

    if request.method == 'GET' or not form.is_valid():
        context = {'form': form}
        data['html_form'] = render_to_string(template_name,
                                             context,
                                             request=request)
        return JsonResponse(data)

    # Correct form submitted

    if not form.instance.id:
        # This is a new instance!
        form.instance.user = request.user
        form.instance.nrows = 0
        form.instance.ncols = 0
        log_type = Log.WORKFLOW_CREATE
        redirect = reverse('dataops:uploadmerge')
    else:
        log_type = Log.WORKFLOW_UPDATE
        redirect = ''

    # Save the instance
    try:
        workflow_item = form.save()
    except IntegrityError:
        form.add_error('name',
                       _('A workflow with that name already exists'))
        context = {'form': form}
        data['html_form'] = render_to_string(template_name,
                                             context,
                                             request=request)
        return JsonResponse(data)

    # Log event
    Log.objects.register(request.user,
                         log_type,
                         workflow_item,
                         {'id': workflow_item.id,
                          'name': workflow_item.name})

    # Set the new workflow as the current one
    workflow_item = get_workflow(request, workflow_item.id)
    if not workflow_item:
        messages.error(request,
                       _('The newly created workflow could not be accessed'))

    # Here we can say that the form processing is done.
    data['form_is_valid'] = True
    data['html_redirect'] = redirect

    return JsonResponse(data)


@user_passes_test(is_instructor)
def workflow_index(request):
    wid = request.session.pop('ontask_workflow_id', None)
    # If removing workflow from session, mark it as available for sharing
    if wid:
        Workflow.unlock_workflow_by_id(wid)
    request.session.pop('ontask_workflow_name', None)

    # Get the available workflows
    workflows = Workflow.objects.filter(
        Q(user=request.user) | Q(shared=request.user)
    ).distinct().values(
        'id',
        'name',
        'description_text',
        'nrows',
        'ncols',
        'modified'
    )

    # Get the available actions
    actions = Action.objects.filter(
        Q(workflow__user=request.user) | Q(workflow__shared=request.user)
    ).distinct().values(
        'id',
        'name',
        'description_text',
        'modified',
        'workflow__name'
    ).order_by('-modified')[:15]

    context = {
        'nwflows': len(workflows),
        'workflows': workflows,
        'actions': actions,
        'nactions': len(actions),
    }

    # Report if Celery is not running properly
    if request.user.is_superuser:
        # Verify that celery is running!
        celery_stats = None
        try:
            celery_stats = inspect().stats()
        except Exception as e:
            pass
        if not celery_stats:
            messages.error(
                request,
                _('WARNING: Celery is not currently running. '
                  'Please configure it correctly.')
            )

    return render(request, 'workflow/md_index.html', context)

class WorkflowDetailView(UserIsInstructor, generic.DetailView):
    """
    @DynamicAttrs
    """
    model = Workflow
    template_name = 'workflow/md_detail.html'
    context_object_name = 'workflow'

    def get_object(self, queryset=None):
        old_obj = super(WorkflowDetailView, self).get_object(queryset=queryset)

        # Check if the workflow is locked
        obj = get_workflow(self.request, old_obj.id)
        return obj

    def get_context_data(self, **kwargs):

        context = super(WorkflowDetailView, self).get_context_data(**kwargs)

        workflow_id = self.request.session.get('ontask_workflow_id', None)
        if not workflow_id:
            return context

        # Get the table information (if it exist)
        context['table_info'] = None
        if ops.workflow_id_has_table(self.object.id):
            context['table_info'] = {
                'num_rows': self.object.nrows,
                'num_cols': self.object.ncols,
                'num_actions': self.object.actions.all().count(),
                'num_attributes': len(self.object.attributes)}

        # Get the key columns
        columns = Column.objects.filter(
            workflow__id=workflow_id,
            is_key=True
        )

        # put the number of key columns in the workflow
        context['num_key_columns'] = columns.count()

        # Guarantee that column position is set for backward compatibility
        columns = self.object.columns.all()
        if any(x.position == 0 for x in columns):
            # At least a column has index equal to zero, so reset all of them
            for idx, c in enumerate(columns):
                c.position = idx + 1
                c.save()

        # Safety check for consistency (only in development)
        if settings.DEBUG:
            assert pandas_db.check_wf_df(self.object)

            # Columns are properly numbered
            cpos = Column.objects.filter(
                workflow__id=workflow_id
            ).values_list('position', flat=True)
            assert sorted(cpos) == range(1, len(cpos) + 1)

        return context

