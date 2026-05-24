<script setup>
import { computed, ref } from 'vue'

const API_BASE_URL = 'http://127.0.0.1:8000'

const fileInput = ref(null)
const forms = ref([])
const currentView = ref('dashboard')
const selectedFormId = ref(null)

const selectedForm = computed(() => {
  return forms.value.find((form) => form.id === selectedFormId.value) ?? null
})

function openFilePicker() {
  fileInput.value?.click()
}

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
}

function backToDashboard() {
  selectedFormId.value = null
  currentView.value = 'dashboard'
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
</script>

<template>
  <main class="bg-light min-vh-100">
    <div class="container py-5">
      <template v-if="currentView === 'dashboard'">
        <div class="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-4">
          <div>
            <p class="text-uppercase fw-bold text-secondary small mb-2">
              Form Digitisation Pipeline
            </p>
            <h1 class="display-5 fw-bold mb-3">Digitised Forms</h1>
            <p class="text-secondary lead mb-0">
              Upload PDF forms, create reusable digital templates, fill entries, and export
              completed PDFs with values overlaid onto the original document.
            </p>
          </div>

          <div class="d-flex align-items-start">
            <input
              ref="fileInput"
              class="d-none"
              type="file"
              accept="application/pdf"
              multiple
              @change="handleFileUpload"
            />

            <button class="btn btn-success fw-semibold" type="button" @click="openFilePicker">
              Upload PDF
            </button>
          </div>
        </div>

        <section class="card border-0 shadow-sm">
          <div class="card-header bg-white py-3">
            <h2 class="h5 mb-1">Forms</h2>
            <p class="text-secondary mb-0">
              Published and draft form templates will appear here.
            </p>
          </div>

          <div v-if="forms.length === 0" class="card-body text-center py-5">
            <h3 class="h6 mb-2">No forms yet</h3>
            <p class="text-secondary mb-0">
              Upload a PDF form to start creating your first digital template.
            </p>
          </div>

          <div v-else class="list-group list-group-flush">
            <div
              v-for="form in forms"
              :key="form.id"
              class="list-group-item d-flex flex-column flex-md-row justify-content-between gap-3 py-3"
            >
              <div>
                <div class="d-flex align-items-center gap-2 mb-1">
                  <h3 class="h6 mb-0">{{ form.name }}</h3>
                  <span class="badge text-bg-warning">{{ form.status }}</span>
                </div>
                  <p class="text-secondary small mb-0">
                    <span v-if="form.extractionStatus === 'extracting'">
                      Extracting suggested fields...
                    </span>
                    <span v-else-if="form.extractionStatus === 'complete'">
                      {{ form.fields.length }} suggested fields found.
                    </span>
                    <span v-else-if="form.extractionStatus === 'failed'" class="text-danger">
                      {{ form.error }}
                    </span>
                  </p>
              </div>

              <div class="d-flex align-items-center gap-2">
                <button
                  class="btn btn-outline-secondary btn-sm"
                  type="button"
                  :disabled="form.extractionStatus === 'extracting'"
                  @click="openBuilder(form.id)"
                >
                  Build Template
                </button>
                <button class="btn btn-outline-secondary btn-sm" type="button" disabled>
                  Fill
                </button>
              </div>
            </div>
          </div>
        </section>
      </template>

      <template v-else-if="currentView === 'builder' && selectedForm">
        <div class="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-4">
          <div>
            <p class="text-uppercase fw-bold text-secondary small mb-2">
              Template Builder
            </p>
            <h1 class="h2 fw-bold mb-2">{{ selectedForm.name }}</h1>
            <p class="text-secondary mb-0">
              Mark the fillable fields on the PDF before publishing this form.
            </p>
          </div>

          <div class="d-flex align-items-start">
            <button class="btn btn-outline-secondary" type="button" @click="backToDashboard">
              Back to Forms
            </button>
          </div>
        </div>

        <div class="row g-4">
          <section class="col-lg-8">
            <div class="card border-0 shadow-sm">
              <div class="card-header bg-white py-3">
                <h2 class="h5 mb-1">PDF Preview</h2>
                <p class="text-secondary mb-0">
                  PDF rendering will go here next.
                </p>
              </div>

              <div class="card-body">
                <div class="border rounded bg-light d-flex align-items-center justify-content-center p-5">
                  <div class="text-center">
                    <p class="fw-semibold mb-1">{{ selectedForm.name }}</p>
                    <p class="text-secondary mb-0">
                      Preview placeholder
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <aside class="col-lg-4">
            <div class="card border-0 shadow-sm">
              <div class="card-header bg-white py-3">
                <h2 class="h5 mb-1">Fields</h2>
                <p class="text-secondary mb-0">
                  Fields added to this template will appear here.
                </p>
              </div>

              <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <span class="text-secondary small">
                    {{ selectedForm.fields.length }} suggested fields
                  </span>

                  <button class="btn btn-success btn-sm" type="button">
                    Add Field
                  </button>
                </div>

                <div v-if="selectedForm.fields.length === 0" class="text-center text-secondary py-4">
                  No fields suggested yet.
                </div>

                <div v-else class="list-group">
                  <div
                    v-for="field in selectedForm.fields"
                    :key="field.id"
                    class="list-group-item px-3 py-2"
                  >
                    <div class="d-flex justify-content-between gap-2">
                      <div>
                        <p class="fw-semibold mb-1">
                          <span v-if="field.group">{{ field.group }} - </span>{{ field.label }}
                        </p>

                        <p class="text-secondary small mb-0">
                          Page {{ field.page }} · {{ field.type }}
                        </p>
                      </div>

                      <div class="d-flex flex-column align-items-end gap-2">
                        <span class="badge text-bg-light border">
                          {{ Math.round(field.confidence * 100) }}%
                        </span>

                        <button
                          class="btn btn-outline-danger btn-sm"
                          type="button"
                          @click="removeField(field.id)"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </template>
    </div>
  </main>
</template>