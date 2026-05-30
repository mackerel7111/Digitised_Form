<script setup>
defineProps({
  selectedForm: {
    type: Object,
    required: true,
  },
  submissionValues: {
    type: Object,
    required: true,
  },
  backToDashboard: {
    type: Function,
    required: true,
  },
  getFillFormItems: {
    type: Function,
    required: true,
  },
  updateSubmissionValue: {
    type: Function,
    required: true,
  },
  downloadFilledPdf: {
    type: Function,
    required: true,
  },
  saveSubmission: {
    type: Function,
    required: true,
  },
})

function getTableCellField(tableItem, rowIndex, columnIndex) {
  return tableItem.fields.find((field) => {
    return field.tableRow === rowIndex && field.tableColumn === columnIndex
  })
}

function getTableColumnLabel(tableItem, columnIndex) {
  const field = tableItem.fields.find((item) => item.tableColumn === columnIndex)

  return field?.tableColumnLabel ?? `Column ${columnIndex}`
}

function getTableRowIndexes(tableItem) {
  const rows = new Set(tableItem.fields.map((f) => f.tableRow))
  return Array.from(rows).sort((a, b) => a - b)
}

function getTableColumnIndexes(tableItem) {
  const cols = new Set(tableItem.fields.map((f) => f.tableColumn))
  return Array.from(cols).sort((a, b) => a - b)
}
</script>

<template>
  <div class="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-4">
    <div>
      <p class="text-uppercase fw-bold text-secondary small mb-2">Fill Form</p>
      <h1 class="h2 fw-bold mb-2">{{ selectedForm.name }}</h1>
      <p class="text-secondary mb-0">
        Complete the digital form. Values will later be overlaid onto the original PDF.
      </p>
    </div>

    <div class="d-flex align-items-start">
      <button class="btn btn-outline-secondary" type="button" @click="backToDashboard">
        Back to Forms
      </button>
    </div>
  </div>

  <section class="card border-0 shadow-sm">
    <div class="card-header bg-white py-3">
      <h2 class="h5 mb-1">Entry</h2>
      <p class="text-secondary mb-0">Generated from the published template fields.</p>
    </div>

    <div class="card-body">
      <div class="row g-3">
      <div
        v-for="item in getFillFormItems(selectedForm.fields)"
        :key="item.id"
        class="col-12"
      >
        <!-- Checkbox group -->
        <div v-if="item.type === 'checkbox_group'" class="border rounded p-3">
          <p class="fw-semibold mb-2">{{ item.label }}</p>

          <div class="d-flex flex-wrap gap-3">
            <div v-for="field in item.fields" :key="field.id" class="form-check">
              <input
                :id="`input-${field.id}`"
                class="form-check-input"
                type="checkbox"
                :checked="submissionValues[field.id]"
                @change="updateSubmissionValue(field.id, $event.target.checked)"
              />
              <label class="form-check-label" :for="`input-${field.id}`">
                {{ field.label }}
              </label>
            </div>
          </div>
        </div>

        <!-- Table group -->
        <div v-else-if="item.type === 'table_group'" class="border rounded p-3">
          <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
            <div>
              <p class="fw-semibold mb-1">{{ item.tableName }}</p>
              <p class="text-secondary small mb-0">
                {{ item.tableColumns }} columns × {{ item.tableRows }} rows
              </p>
            </div>

            <span class="badge text-bg-light border">
              Page {{ item.page }}
            </span>
          </div>

          <div class="table-responsive">
            <table class="table table-bordered align-middle mb-0 fill-table">
              <thead>
                <tr>
                  <th class="text-secondary small fill-table-row-header">Row</th>
                  <th
                    v-for="columnIndex in getTableColumnIndexes(item)"
                    :key="columnIndex"
                    class="text-secondary small"
                  >
                    {{ getTableColumnLabel(item, columnIndex) }}
                  </th>
                </tr>
              </thead>

              <tbody>
                <tr
                  v-for="(rowIndex, rowDisplayIndex) in getTableRowIndexes(item)"
                  :key="rowIndex"
                >
                  <th class="text-secondary small fill-table-row-header">
                    {{ rowDisplayIndex + 1 }}
                  </th>

                  <td
                    v-for="columnIndex in getTableColumnIndexes(item)"
                    :key="columnIndex"
                  >
                    <template v-if="getTableCellField(item, rowIndex, columnIndex)">
                      <input
                        v-if="getTableCellField(item, rowIndex, columnIndex).type === 'text'"
                        class="form-control form-control-sm"
                        type="text"
                        :aria-label="getTableCellField(item, rowIndex, columnIndex).label"
                        :value="submissionValues[getTableCellField(item, rowIndex, columnIndex).id]"
                        @input="
                          updateSubmissionValue(
                            getTableCellField(item, rowIndex, columnIndex).id,
                            $event.target.value,
                          )
                        "
                      />

                      <input
                        v-else-if="getTableCellField(item, rowIndex, columnIndex).type === 'date'"
                        class="form-control form-control-sm"
                        type="date"
                        :aria-label="getTableCellField(item, rowIndex, columnIndex).label"
                        :value="submissionValues[getTableCellField(item, rowIndex, columnIndex).id]"
                        @input="
                          updateSubmissionValue(
                            getTableCellField(item, rowIndex, columnIndex).id,
                            $event.target.value,
                          )
                        "
                      />

                      <input
                        v-else-if="getTableCellField(item, rowIndex, columnIndex).type === 'number'"
                        class="form-control form-control-sm"
                        type="number"
                        :aria-label="getTableCellField(item, rowIndex, columnIndex).label"
                        :value="submissionValues[getTableCellField(item, rowIndex, columnIndex).id]"
                        @input="
                          updateSubmissionValue(
                            getTableCellField(item, rowIndex, columnIndex).id,
                            $event.target.value,
                          )
                        "
                      />

                      <textarea
                        v-else-if="getTableCellField(item, rowIndex, columnIndex).type === 'multiline'"
                        class="form-control form-control-sm"
                        rows="2"
                        :aria-label="getTableCellField(item, rowIndex, columnIndex).label"
                        :value="submissionValues[getTableCellField(item, rowIndex, columnIndex).id]"
                        @input="
                          updateSubmissionValue(
                            getTableCellField(item, rowIndex, columnIndex).id,
                            $event.target.value,
                          )
                        "
                      ></textarea>

                      <div
                        v-else-if="getTableCellField(item, rowIndex, columnIndex).type === 'checkbox'"
                        class="form-check"
                      >
                        <input
                          :id="`input-${getTableCellField(item, rowIndex, columnIndex).id}`"
                          class="form-check-input"
                          type="checkbox"
                          :checked="submissionValues[getTableCellField(item, rowIndex, columnIndex).id]"
                          @change="
                            updateSubmissionValue(
                              getTableCellField(item, rowIndex, columnIndex).id,
                              $event.target.checked,
                            )
                          "
                        />
                      </div>
                    </template>

                    <span v-else class="text-secondary small">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Normal field -->
        <template v-else>
          <label
            v-if="item.field.type !== 'checkbox'"
            class="form-label fw-semibold"
            :for="`input-${item.field.id}`"
          >
            <span v-if="item.field.group">{{ item.field.group }} - </span>{{ item.field.label }}
          </label>

          <input
            v-if="item.field.type === 'text'"
            :id="`input-${item.field.id}`"
            class="form-control"
            type="text"
            :value="submissionValues[item.field.id]"
            @input="updateSubmissionValue(item.field.id, $event.target.value)"
          />

          <input
            v-else-if="item.field.type === 'date'"
            :id="`input-${item.field.id}`"
            class="form-control"
            type="date"
            :value="submissionValues[item.field.id]"
            @input="updateSubmissionValue(item.field.id, $event.target.value)"
          />

          <input
            v-else-if="item.field.type === 'number'"
            :id="`input-${item.field.id}`"
            class="form-control"
            type="number"
            :value="submissionValues[item.field.id]"
            @input="updateSubmissionValue(item.field.id, $event.target.value)"
          />

          <textarea
            v-else-if="item.field.type === 'multiline'"
            :id="`input-${item.field.id}`"
            class="form-control"
            rows="4"
            :value="submissionValues[item.field.id]"
            @input="updateSubmissionValue(item.field.id, $event.target.value)"
          ></textarea>

          <div v-else-if="item.field.type === 'checkbox'" class="form-check">
            <input
              :id="`input-${item.field.id}`"
              class="form-check-input"
              type="checkbox"
              :checked="submissionValues[item.field.id]"
              @change="updateSubmissionValue(item.field.id, $event.target.checked)"
            />
            <label class="form-check-label" :for="`input-${item.field.id}`">
              {{ item.field.label }}
            </label>
          </div>
        </template>
      </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-4">
        <button class="btn btn-outline-secondary" type="button" @click="backToDashboard">
          Cancel
        </button>

        <button class="btn btn-outline-success" type="button" @click="downloadFilledPdf">
          Download Filled PDF
        </button>

        <button class="btn btn-success" type="button" @click="saveSubmission">
          Save Entry
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.fill-table {
  min-width: 720px;
}

.fill-table th,
.fill-table td {
  vertical-align: middle;
}

.fill-table-row-header {
  width: 64px;
  white-space: nowrap;
}

.fill-table input,
.fill-table textarea {
  min-width: 140px;
}
</style>