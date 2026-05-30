<script setup>
import { ref } from 'vue'

defineProps({
  selectedForm: {
    type: Object,
    required: true,
  },
  selectedFieldId: {
    type: String,
    default: null,
  },
  backToDashboard: {
    type: Function,
    required: true,
  },
  saveDraftTemplate: {
    type: Function,
    required: true,
  },
  publishTemplate: {
    type: Function,
    required: true,
  },
  addField: {
    type: Function,
    required: true,
  },
  removeField: {
    type: Function,
    required: true,
  },
  moveField: {
    type: Function,
    required: true,
  },
  updateField: {
    type: Function,
    required: true,
  },
  updateFieldType: {
    type: Function,
    required: true,
  },
  updateFieldRectValue: {
    type: Function,
    required: true,
  },
  getPageImageUrl: {
    type: Function,
    required: true,
  },
  selectField: {
    type: Function,
    required: true,
  },
  getFieldDisplayName: {
    type: Function,
    required: true,
  },
  getFieldBoxClass: {
    type: Function,
    required: true,
  },
  getFieldRowClass: {
    type: Function,
    required: true,
  },
  startFieldDrag: {
    type: Function,
    required: true,
  },
})

const pdfPreviewRef = ref(null)
</script>

<template>
  <div class="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-4">
    <div>
      <p class="text-uppercase fw-bold text-secondary small mb-2">Template Builder</p>
      <h1 class="h2 fw-bold mb-2">{{ selectedForm.name }}</h1>
      <p class="text-secondary mb-0">Mark the fillable fields on the PDF before publishing this form.</p>
    </div>

    <div class="d-flex align-items-start gap-2">
      <button class="btn btn-outline-secondary" type="button" @click="backToDashboard">
        Back to Forms
      </button>

      <button class="btn btn-outline-success" type="button" @click="saveDraftTemplate">
        Save Draft
      </button>

      <button
        class="btn btn-success"
        type="button"
        :disabled="selectedForm.fields.length === 0"
        @click="publishTemplate"
      >
        Publish Template
      </button>
    </div>
  </div>

  <div class="row g-4">
    <section class="col-lg-8">
      <div class="card border-0 shadow-sm">
        <div class="card-header bg-white py-3">
          <h2 class="h5 mb-1">PDF Preview</h2>
          <p class="text-secondary mb-0">PDF rendering will go here next.</p>
        </div>

        <div class="card-body">
          <div ref="pdfPreviewRef" class="pdf-preview border rounded bg-white">
            <img
              class="pdf-page-image"
              :src="getPageImageUrl(selectedForm)"
              :alt="`${selectedForm.name} page 1`"
            />
            <button
              v-for="field in selectedForm.fields"
              :key="field.id"
              type="button"
              :class="getFieldBoxClass(field)"
              :style="{
                left: `${field.rect.x * 100}%`,
                top: `${field.rect.y * 100}%`,
                width: `${field.rect.w * 100}%`,
                height: `${field.rect.h * 100}%`,
              }"
              :title="getFieldDisplayName(field)"
              @pointerdown="startFieldDrag($event, field, pdfPreviewRef)"
            >
              <span
                v-if="field.type === 'date' && field.renderMode === 'date_boxes'"
                class="date-box-preview"
                :style="{ gap: `${field.boxGap ?? 0.4}%` }"
              >
                <span
                  v-for="index in field.boxCount ?? 8"
                  :key="index"
                  class="date-box-preview-cell"
                ></span>
              </span>
            </button>
          </div>
        </div>
      </div>
    </section>

    <aside class="col-lg-4">
      <div class="card border-0 shadow-sm sticky-fields-panel">
        <div class="card-header bg-white py-3">
          <h2 class="h5 mb-1">Fields</h2>
          <p class="text-secondary mb-0">Fields added to this template will appear here.</p>
        </div>

        <div class="card-body fields-card-body">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <span class="text-secondary small">
              {{ selectedForm.fields.length }} suggested fields
            </span>

            <button class="btn btn-success btn-sm" type="button" @click="addField">
              Add Field
            </button>
          </div>

          <div v-if="selectedForm.fields.length === 0" class="text-center text-secondary py-4">
            No fields suggested yet.
          </div>

          <div v-else class="list-group field-list-scroll">
            <div
              v-for="(field, index) in selectedForm.fields"
              :key="field.id"
              :class="getFieldRowClass(field)"
              role="button"
              tabindex="0"
              @click="selectField(field.id)"
              @keydown.enter="selectField(field.id)"
            >
              <div class="d-flex justify-content-between gap-3">
                <div class="flex-grow-1">
                  <label class="form-label small text-secondary mb-1">Field label</label>

                  <input
                    class="form-control form-control-sm mb-2"
                    type="text"
                    :value="field.label"
                    @input="updateField(field.id, { label: $event.target.value })"
                  />

                  <div v-if="field.group" class="text-secondary small mb-2">
                    Group: {{ field.group }}
                  </div>

                  <label class="form-label small text-secondary mb-1">Field type</label>

                  <select
                    class="form-select form-select-sm mb-2"
                    :value="field.type"
                    @change="updateFieldType(field.id, $event.target.value)"
                  >
                    <option value="text">Text</option>
                    <option value="date">Date</option>
                    <option value="number">Number</option>
                    <option value="checkbox">Checkbox</option>
                    <option value="multiline">Multiline</option>
                  </select>

                  <div v-if="field.type === 'date'" class="border rounded p-2 mb-2 bg-light">
                    <label class="form-label small text-secondary mb-1">Date render mode</label>

                    <select
                      class="form-select form-select-sm mb-2"
                      :value="field.renderMode ?? 'single'"
                      @change="updateField(field.id, { renderMode: $event.target.value })"
                    >
                      <option value="single">Single text</option>
                      <option value="date_boxes">Date boxes</option>
                    </select>

                    <div v-if="field.renderMode === 'date_boxes'" class="row g-2">
                      <div class="col-6">
                        <label class="form-label small text-secondary mb-1">Boxes</label>
                        <input
                          class="form-control form-control-sm"
                          type="number"
                          min="1"
                          max="12"
                          step="1"
                          :value="field.boxCount ?? 8"
                          @input="updateField(field.id, { boxCount: Number($event.target.value) })"
                        />
                      </div>

                      <div class="col-6">
                        <label class="form-label small text-secondary mb-1">Gap %</label>
                        <input
                          class="form-control form-control-sm"
                          type="number"
                          min="0"
                          max="5"
                          step="0.1"
                          :value="field.boxGap ?? 0.4"
                          @input="updateField(field.id, { boxGap: Number($event.target.value) })"
                        />
                      </div>
                    </div>
                  </div>

                  <div class="row g-2">
                    <div class="col-6">
                      <label class="form-label small text-secondary mb-1">Width %</label>
                      <input
                        class="form-control form-control-sm"
                        type="number"
                        min="1"
                        max="100"
                        step="0.1"
                        :value="Number((field.rect.w * 100).toFixed(1))"
                        @input="updateFieldRectValue(field.id, 'w', $event.target.value)"
                      />
                    </div>

                    <div class="col-6">
                      <label class="form-label small text-secondary mb-1">Height %</label>
                      <input
                        class="form-control form-control-sm"
                        type="number"
                        min="0.5"
                        max="100"
                        step="0.1"
                        :value="Number((field.rect.h * 100).toFixed(1))"
                        @input="updateFieldRectValue(field.id, 'h', $event.target.value)"
                      />
                    </div>
                  </div>

                  <p class="text-secondary small mt-2 mb-0">
                    Page {{ field.page }} · {{ field.reason }}
                  </p>
                </div>

                <div class="d-flex flex-column align-items-end gap-2">
                  <span class="badge text-bg-light border">
                    {{ Math.round(field.confidence * 100) }}%
                  </span>

                  <button
                    class="btn btn-outline-secondary btn-sm"
                    type="button"
                    :disabled="index === 0"
                    @click="moveField(field.id, 'up')"
                    aria-label="Move up"
                    title="Move up"
                  >
                    &uarr;
                  </button>

                  <button
                    class="btn btn-outline-secondary btn-sm"
                    type="button"
                    :disabled="index === selectedForm.fields.length - 1"
                    @click="moveField(field.id, 'down')"
                    aria-label="Move down"
                    title="Move down"
                  >
                    &darr;
                  </button>

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

<style scoped>
.pdf-preview {
  position: relative;
  max-width: 100%;
  overflow: hidden;
}

.pdf-page-image {
  display: block;
  width: 100%;
  height: auto;
}

.field-box {
  position: absolute;
  padding: 0;
  border: 2px solid;
  border-radius: 3px;
  cursor: pointer;
  opacity: 0.9;
  touch-action: none;
}

.field-box-text {
  border-color: #198754;
  background: rgba(25, 135, 84, 0.14);
}

.field-box-checkbox {
  border-color: #0d6efd;
  background: rgba(13, 110, 253, 0.16);
}

.field-box-multiline {
  border-color: #6f42c1;
  background: rgba(111, 66, 193, 0.14);
}

.field-box-manual {
  border-style: dashed;
}

.field-box-selected {
  border-color: #fd7e14;
  background: rgba(253, 126, 20, 0.2);
  box-shadow: 0 0 0 3px rgba(253, 126, 20, 0.25);
  z-index: 2;
}

.field-row-selected {
  background: #fff3e8;
  border-left: 4px solid #fd7e14;
}

.field-box:hover {
  opacity: 1;
  cursor: move;
}

.sticky-fields-panel {
  position: sticky;
  top: 24px;
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.fields-card-body {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.field-list-scroll {
  min-height: 0;
  max-height: 62vh;
  overflow-y: auto;
}

.field-list-scroll .list-group-item {
  border-left: 0;
  border-right: 0;
}

.field-list-scroll .list-group-item:first-child {
  border-top: 0;
}

.field-list-scroll .list-group-item:last-child {
  border-bottom: 0;
}

.date-box-preview {
  display: grid;
  grid-template-columns: repeat(var(--box-count, 8), 1fr);
  width: 100%;
  height: 100%;
}

.date-box-preview-cell {
  min-width: 0;
  height: 100%;
  border: 1px solid rgba(25, 135, 84, 0.65);
}
</style>
