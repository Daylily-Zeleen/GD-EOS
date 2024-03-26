#include "utils.h"

#include <godot_cpp/variant/utility_functions.hpp>

namespace godot {

String eosg_epic_account_id_to_string(EOS_EpicAccountId accountId) {
    if (accountId == nullptr) {
        return String("");
    }

    char *tempBuffer = (char *)memalloc(EOS_EPICACCOUNTID_MAX_LENGTH + 1);
    int32_t tempBufferSize = EOS_EPICACCOUNTID_MAX_LENGTH + 1;
    EOS_EResult conver_result = EOS_EpicAccountId_ToString(accountId, tempBuffer, &tempBufferSize);

    ERR_FAIL_COND_V_MSG(conver_result != EOS_EResult::EOS_Success, {}, vformat("Fail result code: %d - %s", conver_result, EOS_EResult_ToString(conver_result)));
    return String(tempBuffer);
}

String eosg_product_user_id_to_string(EOS_ProductUserId localUserId) {
    if (localUserId == nullptr) {
        return String("");
    }

    char *tempBuffer = (char *)memalloc(EOS_PRODUCTUSERID_MAX_LENGTH + 1);
    int32_t tempBufferSize = EOS_PRODUCTUSERID_MAX_LENGTH + 1;
    EOS_EResult conver_result = EOS_ProductUserId_ToString(localUserId, tempBuffer, &tempBufferSize);

    ERR_FAIL_COND_V_MSG(conver_result != EOS_EResult::EOS_Success, {}, vformat("Fail result code: %d - %s", conver_result, EOS_EResult_ToString(conver_result)));
    return String(tempBuffer);
}
} //namespace godot