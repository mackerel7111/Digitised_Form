<script setup>
import { computed, onMounted, ref } from 'vue'

import DashboardView from './components/DashboardView.vue'
import EntriesView from './components/EntriesView.vue'
import FillFormView from './components/FillFormView.vue'
import TemplateBuilderView from './components/TemplateBuilderView.vue'

const API_BASE_URL = 'http://127.0.0.1:8000'

const forms = ref([])
const currentView = ref('dashboard')
const selectedFormId = ref(null)
const selectedFieldId = ref(null)
const dragState = ref(null)
const submissionValues = ref({})
const selectedSubmissions = ref([])

const selectedForm = computed(() => {
  return forms.value.find((form) => form.id === selectedFormId.value) ?? null
})

async function loadForms() {
  const response = await fetch(`${API_BASE_URL}/api/forms`)

  if (!response.ok) {
    console.error('Could not load saved forms')
    return
  }

  forms.value = await response.json()
}

async function saveTemplate(form) {
  const response = await fetch(`${API_BASE_URL}/api/forms/${form.id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      fields: form.fields,
      status: form.status,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail ?? 'Could not save template')
  }

  return response.json()
}

async function saveSubmission() {
  if (!selectedForm.value) {
    return
  }

  try {
    const savedSubmission = await saveSubmissionToBackend(
      selectedForm.value.id,
      submissionValues.value,
    )

    forms.value = forms.value.map((form) => {
      if (form.id !== selectedForm.value.id) {
        return form
      }

      return {
        ...form,
        submissions: [...(form.submissions ?? []), savedSubmission],
      }
    })

    backToDashboard()
  } catch (error) {
    alert(error.message)
  }
}

onMounted(() => {
  loadForms()
})

async function extractFields(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/extract-fields`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail ?? 'Could not extract fields')
  }

  return response.json()
}

async function handleFileUpload(event) {
  const selectedFiles = Array.from(event.target.files ?? [])
  const pdfFiles = selectedFiles.filter((file) => file.type === 'application/pdf')

  for (const file of pdfFiles) {
    const temporaryId = crypto.randomUUID()

    const draftForm = {
      id: temporaryId,
      name: file.name,
      status: 'Draft',
      file,
      fields: [],
      extractionStatus: 'extracting',
      error: null,
    }

    forms.value = [draftForm, ...forms.value]

    try {
      const result = await extractFields(file)

      forms.value = forms.value.map((form) => {
        if (form.id !== temporaryId) {
          return form
        }

        return {
          ...form,
          id: result.id,
          fields: result.fields,
          extractionStatus: 'complete',
        }
      })
    } catch (error) {
      forms.value = forms.value.map((form) => {
        if (form.id !== temporaryId) {
          return form
        }

        return {
          ...form,
          extractionStatus: 'failed',
          error: error.message,
        }
      })
    }
  }

  event.target.value = ''
}

function openBuilder(formId) {
  selectedFormId.value = formId
  currentView.value = 'builder'
  selectedFieldId.value = null
}

function backToDashboard() {
  selectedFormId.value = null
  currentView.value = 'dashboard'
  selectedFieldId.value = null
  selectedSubmissions.value = []
}

async function publishTemplate() {
  if (!selectedForm.value) {
    return
  }

  const formToPublish = {
    ...selectedForm.value,
    status: 'Published',
  }

  try {
    const savedForm = await saveTemplate(formToPublish)

    forms.value = forms.value.map((form) => {
      if (form.id !== savedForm.id) {
        return form
      }

      return savedForm
    })

    backToDashboard()
  } catch (error) {
    alert(error.message)
  }
}

async function saveDraftTemplate() {
  if (!selectedForm.value) {
    return
  }

  try {
    const savedForm = await saveTemplate(selectedForm.value)

    forms.value = forms.value.map((form) => {
      if (form.id !== savedForm.id) {
        return form
      }

      return savedForm
    })

    alert('Draft saved')
  } catch (error) {
    alert(error.message)
  }
}

async function saveSubmissionToBackend(formId, values) {
  const response = await fetch(`${API_BASE_URL}/api/forms/${formId}/submissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ values }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail ?? 'Could not save submission')
  }

  return response.json()
}

function getFillFormItems(fields) {
  const items = []
  const checkboxGroups = new Map()
  const tableGroups = new Map()

  for (const field of fields) {
    if (field.tableId) {
      if (!tableGroups.has(field.tableId)) {
        const tableItem = {
          id: field.tableId,
          type: 'table_group',
          tableId: field.tableId,
          tableName: field.tableName ?? 'Table',
          page: field.page,
          tableRows: field.tableRows ?? field.tableRow ?? 1,
          tableColumns: field.tableColumns ?? field.tableColumn ?? 1,
          fields: [],
        }

        tableGroups.set(field.tableId, tableItem)
        items.push(tableItem)
      }

      const tableItem = tableGroups.get(field.tableId)

      tableItem.fields.push(field)
      tableItem.tableRows = Math.max(
        tableItem.tableRows,
        field.tableRows ?? field.tableRow ?? 1,
      )
      tableItem.tableColumns = Math.max(
        tableItem.tableColumns,
        field.tableColumns ?? field.tableColumn ?? 1,
      )

      continue
    }

    if (field.type === 'checkbox' && field.group) {
      if (!checkboxGroups.has(field.group)) {
        const groupItem = {
          id: `group_${field.group}`,
          type: 'checkbox_group',
          label: field.group,
          fields: [],
        }

        checkboxGroups.set(field.group, groupItem)
        items.push(groupItem)
      }

      checkboxGroups.get(field.group).fields.push(field)
      continue
    }

    items.push({
      id: field.id,
      type: 'field',
      field,
    })
  }

  for (const item of items) {
    if (item.type === 'table_group') {
      item.fields.sort((a, b) => {
        const rowDiff = (a.tableRow ?? 0) - (b.tableRow ?? 0)

        if (rowDiff !== 0) {
          return rowDiff
        }

        return (a.tableColumn ?? 0) - (b.tableColumn ?? 0)
      })
    }
  }

  return items
}

function removeField(fieldId) {
  if (!selectedForm.value) {
    return
  }

  forms.value = forms.value.map((form) => {
    if (form.id !== selectedForm.value.id) {
      return form
    }

    return {
      ...form,
      fields: form.fields.filter((field) => field.id !== fieldId),
    }
  })
}

function moveField(fieldId, direction) {
  if (!selectedForm.value) {
    return
  }

  const currentFormId = selectedForm.value.id
  const delta = direction === 'up' ? -1 : 1

  forms.value = forms.value.map((form) => {
    if (form.id !== currentFormId) {
      return form
    }

    const fields = [...form.fields]
    const currentIndex = fields.findIndex((field) => field.id === fieldId)

    if (currentIndex === -1) {
      return form
    }

    const nextIndex = currentIndex + delta

    if (nextIndex < 0 || nextIndex >= fields.length) {
      return form
    }

    const [movedField] = fields.splice(currentIndex, 1)
    fields.splice(nextIndex, 0, movedField)

    return {
      ...form,
      fields,
    }
  })
}

async function loadSubmissions(formId) {
  const response = await fetch(`${API_BASE_URL}/api/forms/${formId}/submissions`)

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail ?? 'Could not load submissions')
  }

  return response.json()
}

async function openEntries(formId) {
  const form = forms.value.find((item) => item.id === formId)

  if (!form) {
    return
  }

  try {
    selectedFormId.value = formId
    selectedFieldId.value = null
    selectedSubmissions.value = await loadSubmissions(formId)
    currentView.value = 'entries'
  } catch (error) {
    alert(error.message)
  }
}

async function downloadSubmissionPdf(submission) {
  if (!selectedForm.value) {
    return
  }

  const response = await fetch(`${API_BASE_URL}/api/uploads/${selectedForm.value.id}/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      fields: selectedForm.value.fields,
      values: submission.values,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    alert(error?.detail ?? 'Could not export filled PDF')
    return
  }

  const blob = await response.blob()
  const downloadUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = downloadUrl
  link.download = `${selectedForm.value.name.replace(/\.pdf$/i, '')}-${submission.id}.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()

  URL.revokeObjectURL(downloadUrl)
}

function addField() {
  if (!selectedForm.value) {
    return
  }

  const newField = {
    id: `manual_${crypto.randomUUID()}`,
    label: 'New field',
    type: 'text',
    page: 1,
    rect: {
      x: 0.1,
      y: 0.1,
      w: 0.3,
      h: 0.03,
    },
    confidence: 1,
    reason: 'manually added',
  }

  forms.value = forms.value.map((form) => {
    if (form.id !== selectedForm.value.id) {
      return form
    }

    return {
      ...form,
      fields: [...form.fields, newField],
    }
  })
}

function updateField(fieldId, updates) {
  if (!selectedForm.value) {
    return
  }

  forms.value = forms.value.map((form) => {
    if (form.id !== selectedForm.value.id) {
      return form
    }

    return {
      ...form,
      fields: form.fields.map((field) => {
        if (field.id !== fieldId) {
          return field
        }

        return {
          ...field,
          ...updates,
        }
      }),
    }
  })
}

function updateTableColumnLabel(tableId, columnIndex, label) {
  if (!selectedForm.value) {
    return
  }

  forms.value = forms.value.map((form) => {
    if (form.id !== selectedForm.value.id) {
      return form
    }

    return {
      ...form,
      fields: form.fields.map((field) => {
        if (field.tableId !== tableId || field.tableColumn !== columnIndex) {
          return field
        }

        return {
          ...field,
          tableColumnLabel: label,
        }
      }),
    }
  })
}

function updateTableName(tableId, name) {
  if (!selectedForm.value) {
    return
  }

  forms.value = forms.value.map((form) => {
    if (form.id !== selectedForm.value.id) {
      return form
    }

    return {
      ...form,
      fields: form.fields.map((field) => {
        if (field.tableId !== tableId) {
          return field
        }

        return {
          ...field,
          tableName: name,
        }
      }),
    }
  })
}

function updateFieldType(fieldId, type) {
  const updates = { type }

  if (type === 'date') {
    updates.renderMode = 'single'
    updates.dateFormat = 'DDMMYYYY'
    updates.boxCount = 8
    updates.boxGap = 0.4
  }

  if (type === 'table') {
    updates.tableColumns = 3
    updates.tableRows = 3
  }

  updateField(fieldId, updates)
}

function updateFieldRectValue(fieldId, key, value) {
  const numericValue = Number(value)

  if (!Number.isFinite(numericValue)) {
    return
  }

  const normalizedValue = numericValue / 100

  updateFieldRect(fieldId, {
    [key]: Number(normalizedValue.toFixed(4)),
  })
}

function getPageImageUrl(form) {
  return `${API_BASE_URL}/api/uploads/${form.id}/page/1.png`
}

function selectField(fieldId) {
  selectedFieldId.value = fieldId
}

function getFieldDisplayName(field) {
  return field.group ? `${field.group} - ${field.label}` : field.label
}

function getFieldBoxClass(field) {
  return {
    'field-box': true,
    'field-box-text': ['text', 'date', 'number'].includes(field.type),
    'field-box-checkbox': field.type === 'checkbox',
    'field-box-multiline': ['multiline', 'table'].includes(field.type),
    'field-box-manual': field.reason === 'manually added',
    'field-box-selected': field.id === selectedFieldId.value,
  }
}

function getFieldRowClass(field) {
  return {
    'list-group-item': true,
    'px-3': true,
    'py-2': true,
    'field-row-selected': field.id === selectedFieldId.value,
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function updateFieldRect(fieldId, rectUpdates) {
  if (!selectedForm.value) {
    return
  }

  forms.value = forms.value.map((form) => {
    if (form.id !== selectedForm.value.id) {
      return form
    }

    return {
      ...form,
      fields: form.fields.map((field) => {
        if (field.id !== fieldId) {
          return field
        }

        return {
          ...field,
          rect: {
            ...field.rect,
            ...rectUpdates,
          },
        }
      }),
    }
  })
}

function startFieldDrag(event, field, previewElement) {
  const targetPreviewElement = previewElement?.value ?? previewElement

  if (!targetPreviewElement) {
    return
  }

  event.preventDefault()
  event.stopPropagation()

  selectField(field.id)

  const previewRect = targetPreviewElement.getBoundingClientRect()

  dragState.value = {
    fieldId: field.id,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX: field.rect.x,
    startY: field.rect.y,
    width: field.rect.w,
    height: field.rect.h,
    previewWidth: previewRect.width,
    previewHeight: previewRect.height,
  }

  window.addEventListener('pointermove', handleFieldDrag)
  window.addEventListener('pointerup', stopFieldDrag)
}

function handleFieldDrag(event) {
  if (!dragState.value) {
    return
  }

  const deltaX = (event.clientX - dragState.value.startClientX) / dragState.value.previewWidth
  const deltaY = (event.clientY - dragState.value.startClientY) / dragState.value.previewHeight

  const nextX = clamp(dragState.value.startX + deltaX, 0, 1 - dragState.value.width)
  const nextY = clamp(dragState.value.startY + deltaY, 0, 1 - dragState.value.height)

  updateFieldRect(dragState.value.fieldId, {
    x: Number(nextX.toFixed(4)),
    y: Number(nextY.toFixed(4)),
  })
}

function stopFieldDrag() {
  dragState.value = null
  window.removeEventListener('pointermove', handleFieldDrag)
  window.removeEventListener('pointerup', stopFieldDrag)
}

function openFiller(formId) {
  const form = forms.value.find((item) => item.id === formId)

  if (!form || form.status !== 'Published') {
    return
  }

  selectedFormId.value = formId
  selectedFieldId.value = null

  const initialValues = {}

  for (const field of form.fields) {
    initialValues[field.id] = field.type === 'checkbox' ? false : ''
  }

  submissionValues.value = initialValues
  currentView.value = 'filler'
}

function updateSubmissionValue(fieldId, value) {
  submissionValues.value = {
    ...submissionValues.value,
    [fieldId]: value,
  }
}

async function downloadFilledPdf() {
  if (!selectedForm.value) {
    return
  }

  const response = await fetch(`${API_BASE_URL}/api/uploads/${selectedForm.value.id}/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      fields: selectedForm.value.fields,
      values: submissionValues.value,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    alert(error?.detail ?? 'Could not export filled PDF')
    return
  }

  const blob = await response.blob()
  const downloadUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = downloadUrl
  link.download = `${selectedForm.value.name.replace(/\.pdf$/i, '')}-filled.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()

  URL.revokeObjectURL(downloadUrl)
}
</script>

<template>
  <main class="bg-light min-vh-100">
    <div class="container py-5">
      <DashboardView
        v-if="currentView === 'dashboard'"
        :forms="forms"
        @upload="handleFileUpload"
        @open-builder="openBuilder"
        @open-filler="openFiller"
        @open-entries="openEntries"
      />

      <TemplateBuilderView
        v-else-if="currentView === 'builder' && selectedForm"
        :selected-form="selectedForm"
        :selected-field-id="selectedFieldId"
        :back-to-dashboard="backToDashboard"
        :save-draft-template="saveDraftTemplate"
        :publish-template="publishTemplate"
        :add-field="addField"
        :remove-field="removeField"
        :move-field="moveField"
        :update-field="updateField"
        :update-field-type="updateFieldType"
        :update-table-column-label="updateTableColumnLabel"
        :update-table-name="updateTableName"
        :update-field-rect-value="updateFieldRectValue"
        :get-page-image-url="getPageImageUrl"
        :select-field="selectField"
        :get-field-display-name="getFieldDisplayName"
        :get-field-box-class="getFieldBoxClass"
        :get-field-row-class="getFieldRowClass"
        :start-field-drag="startFieldDrag"
      />

      <FillFormView
        v-else-if="currentView === 'filler' && selectedForm"
        :selected-form="selectedForm"
        :submission-values="submissionValues"
        :back-to-dashboard="backToDashboard"
        :get-fill-form-items="getFillFormItems"
        :update-submission-value="updateSubmissionValue"
        :download-filled-pdf="downloadFilledPdf"
        :save-submission="saveSubmission"
      />

      <EntriesView
        v-else-if="currentView === 'entries' && selectedForm"
        :selected-form="selectedForm"
        :selected-submissions="selectedSubmissions"
        :back-to-dashboard="backToDashboard"
        :download-submission-pdf="downloadSubmissionPdf"
      />
    </div>
  </main>
</template>
