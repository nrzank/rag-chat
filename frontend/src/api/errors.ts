import type { ApiErrorBody } from "./types";

const MESSAGES: Record<string, string> = {
  document_not_found: "Документ не найден",
  conversation_not_found: "Диалог не найден",
  unsupported_file_type: "Такой тип файла не поддерживается",
  file_too_large: "Файл слишком большой",
  document_parsing_failed: "Не удалось разобрать файл",
  validation_error: "Некорректный запрос",
  not_found: "Не найдено",
  internal_error: "Что-то пошло не так на сервере",
  network_error: "Сервер недоступен",
};

export class ApiError extends Error {
  code: string;
  params: Record<string, unknown>;

  constructor(code: string, params: Record<string, unknown> = {}) {
    super(MESSAGES[code] ?? MESSAGES.internal_error);
    this.code = code;
    this.params = params;
  }
}

export function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return MESSAGES.network_error;
}

export function toApiError(body: unknown): ApiError {
  const parsed = body as Partial<ApiErrorBody>;
  return new ApiError(parsed?.code ?? "internal_error", parsed?.params ?? {});
}
