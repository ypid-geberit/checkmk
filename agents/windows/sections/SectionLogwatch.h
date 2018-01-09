// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef SectionLogwatch_h
#define SectionLogwatch_h

#include "Configurable.h"
#include "Section.h"
#include "types.h"

typedef struct _BY_HANDLE_FILE_INFORMATION BY_HANDLE_FILE_INFORMATION;

typedef std::vector<globline_container> GlobListT;

template <>
globline_container from_string<globline_container>(const WinApiAdaptor &winapi,
                                                   const std::string &value);

// A bogus stream operator for globline_container just to enable template
// instantiation for ListConfigurable<GlobListT>.
inline std::ostream &operator<<(std::ostream &os, const globline_container &) {
    return os << "[reference to globline_container instance]";
}

class GlobListConfigurable
    : public ListConfigurable<GlobListT, BlockMode::Nop<GlobListT>,
                              AddMode::PriorityAppendGrouped<GlobListT>> {
    typedef ListConfigurable<GlobListT, BlockMode::Nop<GlobListT>,
                             AddMode::PriorityAppendGrouped<GlobListT>>
        SuperT;

public:
    GlobListConfigurable(Configuration &config, const char *section,
                         const WinApiAdaptor &winapi)
        : SuperT(config, section, "textfile", winapi) {
        config.reg(section, "warn", this);
        config.reg(section, "crit", this);
        config.reg(section, "ignore", this);
        config.reg(section, "ok", this);
    }

    virtual void feed(const std::string &key,
                      const std::string &value) override {
        if (key == "textfile") {
            SuperT::feed(key, value);
        } else {
            SuperT::feedInner(key, value);
        }
    }
};

logwatch_textfile parseLogwatchStateLine(const std::string &line);

class SectionLogwatch : public Section {
    struct ProcessTextfileResponse {
        bool found_match;
        int unprocessed_bytes;
    };

    typedef std::pair<std::string, FILETIME> FileEntryType;

public:
    SectionLogwatch(Configuration &config, Logger *logger,
                    const WinApiAdaptor &winapi);
    virtual ~SectionLogwatch();

protected:
    virtual bool produceOutputInner(std::ostream &out) override;

private:
    void init();

    void eraseFilesOlder(std::vector<std::string> &file_names,
                         uint64_t file_id);

    void cleanupTextfiles();

    void loadLogwatchOffsets();

    bool getFileInformation(const std::string &filename,
                            BY_HANDLE_FILE_INFORMATION *info);

    void saveOffsets(const std::string &logwatch_statefile);

    std::vector<std::string> sortedByTime(
        const std::vector<FileEntryType> &entries);
    std::vector<logwatch_textfile>::iterator findLogwatchTextfile(
        const std::string &name);

    bool updateCurrentRotatedTextfile(logwatch_textfile &textfile);

    logwatch_textfile &addNewLogwatchTextfile(
        const char *full_filename, const glob_token &token,
        const condition_patterns_t &patterns);

    void updateLogwatchTextfile(logwatch_textfile &textfile);

    void updateRotatedLogfile(const std::string &pattern,
                              logwatch_textfile &textfile);

    logwatch_textfile &addNewRotatedLogfile(
        const std::string &pattern, const std::vector<std::string> &filenames,
        const glob_token &token, condition_patterns_t &patterns);

    void updateOrCreateLogwatchTextfile(const char *full_filename,
                                        const glob_token &token,
                                        condition_patterns_t &patterns);

    void updateOrCreateRotatedLogfile(const std::vector<std::string> &filenames,
                                      const glob_token &token,
                                      condition_patterns_t &patterns);
    std::vector<FileEntryType> globMatches(const std::string &pattern);

    ProcessTextfileResponse processTextfileDefault(
        std::ifstream &file, const logwatch_textfile &textfile,
        std::ostream &out, bool write_output);

    ProcessTextfileResponse processTextfileUnicode(
        std::ifstream &file, const logwatch_textfile &textfile,
        std::ostream &out, bool write_output);

    ProcessTextfileResponse processTextfile(std::ifstream &file,
                                            const logwatch_textfile &textfile,
                                            std::ostream &out,
                                            bool write_output);

    void processTextfile(std::ostream &out, logwatch_textfile &textfile);

    void processGlobExpression(glob_token &glob_token,
                               condition_patterns_t &patterns);

    GlobListConfigurable _globlines;
    std::vector<logwatch_textfile> _textfiles;
    std::vector<logwatch_textfile> _hints;
    bool _offsets_loaded{false};
    bool _initialised{false};
};

#endif  // SectionLogwatch_h
