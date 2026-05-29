<script setup>
import { ref } from 'vue'

defineProps({
  forms: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['upload', 'open-builder', 'open-filler', 'open-entries'])

const fileInput = ref(null)

function openFilePicker() {
  fileInput.value?.click()
}
</script>

<template>
  <div class="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-4">
    <div>
      <p class="text-uppercase fw-bold text-secondary small mb-2">Form Digitisation Pipeline</p>
      <h1 class="display-5 fw-bold mb-3">Digitised Forms</h1>
      <p class="text-secondary lead mb-0">
        Upload PDF forms, create reusable digital templates, fill entries, and export completed PDFs
        with values overlaid onto the original document.
      </p>
    </div>

    <div class="d-flex align-items-start">
      <input
        ref="fileInput"
        class="d-none"
        type="file"
        accept="application/pdf"
        multiple
        @change="emit('upload', $event)"
      />

      <button class="btn btn-success fw-semibold" type="button" @click="openFilePicker">
        Upload PDF
      </button>
    </div>
  </div>

  <section class="card border-0 shadow-sm">
    <div class="card-header bg-white py-3">
      <h2 class="h5 mb-1">Forms</h2>
      <p class="text-secondary mb-0">Published and draft form templates will appear here.</p>
    </div>

    <div v-if="forms.length === 0" class="card-body text-center py-5">
      <h3 class="h6 mb-2">No forms yet</h3>
      <p class="text-secondary mb-0">Upload a PDF form to start creating your first digital template.</p>
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
            <span
              class="badge"
              :class="form.status === 'Published' ? 'text-bg-success' : 'text-bg-warning'"
            >
              {{ form.status }}
            </span>
          </div>
          <p class="text-secondary small mb-0">
            <span v-if="form.extractionStatus === 'extracting'">Extracting suggested fields...</span>
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
            @click="emit('open-builder', form.id)"
          >
            Build Template
          </button>
          <button
            class="btn btn-outline-success btn-sm"
            type="button"
            :disabled="form.status !== 'Published'"
            @click="emit('open-filler', form.id)"
          >
            Fill
          </button>

          <button
            class="btn btn-outline-primary btn-sm"
            type="button"
            :disabled="form.status !== 'Published'"
            @click="emit('open-entries', form.id)"
          >
            View Entries
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
